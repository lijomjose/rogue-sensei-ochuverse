"""Start the offline game on loopback. No third-party Python dependencies."""
import sys
if sys.version_info < (3, 10):
    raise SystemExit("Python 3.10 or newer is required. Please update Python.")

import argparse
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import secrets
import shutil
import subprocess
import tempfile
import threading
import webbrowser

from runtime.runner import evaluate

ROOT = Path(__file__).resolve().parent
STATIC = {"": ("index.html", "text/html; charset=utf-8"),
          "style.css": ("style.css", "text/css; charset=utf-8"),
          "game.js": ("game.js", "text/javascript; charset=utf-8")}


def check_compiler(compiler):
    resolved = shutil.which(compiler)
    if not resolved:
        raise RuntimeError("GCC was not found. See docs/INSTALL.md, install GCC and launch again.")
    with tempfile.TemporaryDirectory(prefix="ochu-check-") as tmp:
        source = Path(tmp) / "check.c"
        binary = Path(tmp) / ("check.exe" if sys.platform == "win32" else "check")
        source.write_text("int main(void) { return 0; }", encoding="utf-8")
        try:
            built = subprocess.run([resolved, "-std=c11", str(source), "-o", str(binary)],
                                   capture_output=True, timeout=10)
            if built.returncode:
                raise RuntimeError("GCC cannot compile a C program. Check your compiler installation.")
            ran = subprocess.run([str(binary)], capture_output=True, timeout=3)
            if ran.returncode:
                raise RuntimeError("Compiled programs cannot run. Check compiler runtime libraries.")
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise RuntimeError("The compiler check failed: " + str(exc)) from exc
    return resolved


def valid_save(value):
    return (isinstance(value, dict) and type(value.get("stage")) is int
            and 0 <= value["stage"] <= 3 and isinstance(value.get("source"), str)
            and len(value["source"].encode("utf-8")) <= 16 * 1024)


class GameServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, compiler, sanitize=None, save_path=None):
        super().__init__(("127.0.0.1", 0), Handler)
        self.compiler = compiler
        self.sanitize = sanitize
        self.token = secrets.token_urlsafe(32)
        self.prefix = "/" + self.token + "/"
        self.origin = "http://127.0.0.1:" + str(self.server_port)
        self.slot = threading.Lock()
        self.save_lock = threading.Lock()
        self.save_path = Path(save_path) if save_path else Path.home() / ".rogue-sensei-ochuverse" / "pointerra.json"

    @property
    def game_url(self):
        return self.origin + self.prefix


class Handler(BaseHTTPRequestHandler):
    def setup(self):
        super().setup()
        self.connection.settimeout(5)

    def log_message(self, *_):
        pass  # Do not log the private session URL.

    def send_payload(self, status, data, content_type="application/json"):
        body = json.dumps(data).encode() if content_type == "application/json" else data
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; img-src 'self' data:; frame-ancestors 'none'; base-uri 'none'")
        self.end_headers()
        self.wfile.write(body)

    def valid_host(self):
        return self.headers.get("Host") == self.server.origin.removeprefix("http://")

    def do_GET(self):
        if not self.valid_host() or not self.path.startswith(self.server.prefix):
            return self.send_payload(404, {"error": "Unknown session"})
        relative = self.path[len(self.server.prefix):]
        if relative == "api/save":
            with self.server.save_lock:
                try:
                    saved = json.loads(self.server.save_path.read_text(encoding="utf-8"))
                    if not valid_save(saved):
                        raise ValueError("Invalid save")
                except FileNotFoundError:
                    saved = {}
                except (ValueError, OSError):
                    return self.send_payload(500, {"error": "Could not read your journal"})
            return self.send_payload(200, saved)
        if relative not in STATIC:
            return self.send_payload(404, {"error": "Not found"})
        name, mime = STATIC[relative]
        return self.send_payload(200, (ROOT / "game" / name).read_bytes(), mime)

    def do_POST(self):
        if (not self.valid_host() or self.path not in (self.server.prefix + "api/run", self.server.prefix + "api/save")
                or self.headers.get("Origin") != self.server.origin
                or self.headers.get("X-Ochu-Session") != self.server.token):
            return self.send_payload(403, {"error": "Invalid local session"})
        if self.headers.get("Content-Type") != "application/json":
            return self.send_payload(415, {"error": "Expected JSON"})
        try:
            size = int(self.headers.get("Content-Length", "0"))
            if not 0 < size <= 20 * 1024:
                return self.send_payload(413, {"error": "Attempt is too large"})
            payload = json.loads(self.rfile.read(size))
            if self.path.endswith("api/save"):
                if not valid_save(payload):
                    return self.send_payload(400, {"error": "Invalid journal"})
                with self.server.save_lock:
                    try:
                        path = self.server.save_path
                        path.parent.mkdir(parents=True, exist_ok=True)
                        temporary = path.with_suffix(".tmp")
                        temporary.write_text(json.dumps(payload), encoding="utf-8")
                        os.replace(temporary, path)
                    except OSError:
                        return self.send_payload(500, {"error": "Could not save your journal"})
                return self.send_payload(200, {"saved": True})
            source = payload.get("source") if isinstance(payload, dict) else None
            if not isinstance(source, str) or len(source.encode("utf-8")) > 16 * 1024:
                return self.send_payload(400, {"error": "Supply a C function up to 16 KiB"})
        except (ValueError, UnicodeError):
            return self.send_payload(400, {"error": "Invalid JSON"})
        if not self.server.slot.acquire(blocking=False):
            return self.send_payload(429, {"error": "Another attempt is running. Please retry shortly."})
        try:
            result = evaluate(source, compiler=self.server.compiler, sanitize=self.server.sanitize)
            return self.send_payload(200, result)
        except (OSError, subprocess.SubprocessError):
            return self.send_payload(500, {"error": "Execution failed. Check your local compiler installation."})
        finally:
            self.server.slot.release()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--no-browser", action="store_true")
    parser.add_argument("--compiler", default="gcc")
    parser.add_argument("--no-sanitizers", action="store_true",
                        help="Compatibility mode; removes memory diagnostics")
    args = parser.parse_args()
    try:
        compiler = check_compiler(args.compiler)
    except RuntimeError as exc:
        print(exc)
        return 1
    with GameServer(compiler, False if args.no_sanitizers else None) as server:
        print("Rogue Sensei · Pointerra development preview")
        print("Open:", server.game_url)
        print("Keep this window open. Press Ctrl+C to stop the game.")
        if not args.no_browser:
            webbrowser.open(server.game_url)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print("\nGame stopped.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
