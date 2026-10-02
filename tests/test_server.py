import http.client
import json
from pathlib import Path
import sys
import tempfile
import threading
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from launcher import GameServer, check_compiler
from runtime.runner import evaluate

class LocalGameTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.save_path = Path(self.tmp.name) / "save.json"
        self.server = GameServer("gcc", save_path=self.save_path)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()
        self.tmp.cleanup()

    def request(self, path, data=None, origin=True, token=True, host=None):
        conn = http.client.HTTPConnection("127.0.0.1", self.server.server_port)
        headers = {}
        if origin: headers["Origin"] = self.server.origin
        if token: headers["X-Ochu-Session"] = self.server.token
        if host: headers["Host"] = host
        if data is not None: headers["Content-Type"] = "application/json"
        conn.request("POST" if data is not None else "GET", path,
                     json.dumps(data) if data is not None else None, headers)
        response = conn.getresponse()
        result = response.status, response.read()
        conn.close()
        return result

    def test_complete_attempt_and_save_survive_new_session(self):
        payload = {"stage": 1, "source": "void charge(int *p) { *p += 20; }"}
        self.assertEqual(self.request(self.server.prefix + "api/save", payload)[0], 200)
        status, body = self.request(self.server.prefix + "api/run", {"source": payload["source"]})
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body)["status"], "passed")
        other = GameServer("gcc", save_path=self.save_path)
        thread = threading.Thread(target=other.serve_forever, daemon=True)
        thread.start()
        try:
            conn = http.client.HTTPConnection("127.0.0.1", other.server_port)
            conn.request("GET", other.prefix + "api/save")
            response = conn.getresponse()
            self.assertEqual(json.loads(response.read()), payload)
            conn.close()
        finally:
            other.shutdown(); other.server_close(); thread.join()

    def test_unrelated_web_pages_cannot_submit_code(self):
        path = self.server.prefix + "api/run"
        source = {"source": "void charge(int *p) { *p += 20; }"}
        self.assertEqual(self.request(path, source, origin=False)[0], 403)
        self.assertEqual(self.request(path, source, token=False)[0], 403)
        self.assertEqual(self.request(path, source, host="evil.example")[0], 403)
        self.assertEqual(self.request("/api/run", source)[0], 403)

    def test_only_game_assets_are_served(self):
        self.assertEqual(self.request(self.server.prefix)[0], 200)
        self.assertEqual(self.request(self.server.prefix + "../launcher.py")[0], 404)
        self.assertEqual(self.request(self.server.prefix + "docs/STORY_BIBLE.md")[0], 404)

    def test_busy_attempt_does_not_start_another_program(self):
        with self.server.slot:
            status, _ = self.request(self.server.prefix + "api/run", {"source": "void charge(int *p) {}"})
        self.assertEqual(status, 429)

    def test_invalid_journal_does_not_replace_saved_progress(self):
        self.assertEqual(self.request(self.server.prefix + "api/save", {"stage": 99, "source": "bad"})[0], 400)
        self.assertFalse(self.save_path.exists())

    def test_missing_compiler_has_actionable_message(self):
        with self.assertRaisesRegex(RuntimeError, "GCC was not found"):
            check_compiler("ochu-nonexistent-compiler")

    def test_plain_compiler_mode_still_accepts_correct_c(self):
        result = evaluate("void charge(int *p) { *p += 20; }", sanitize=False)
        self.assertEqual(result["status"], "passed")
        self.assertFalse(result["sanitizers"])

    def test_unbounded_printing_is_stopped(self):
        result = evaluate('void charge(int *p) { (void)p; for (;;) puts("overflow"); }')
        self.assertEqual(result["cases"][0]["status"], "output_limit")

if __name__ == "__main__": unittest.main()
