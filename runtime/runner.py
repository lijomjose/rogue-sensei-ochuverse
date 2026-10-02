"""Trusted local development only: compile real C and collect JSON trace events."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import tempfile
import time
import platform

ROOT = Path(__file__).resolve().parent
MAX_OUTPUT = 64 * 1024
CASES = (0, 40, 75)

TRACE_HEADER = r'''
#include <stdio.h>
#include <stdlib.h>

static void ochu_trace_pointer(const char *name,
                               const void *pointer_address,
                               const void *stored_address)
{
    printf("{\"event\":\"pointer\",\"name\":\"%s\","
           "\"pointer_address\":\"%p\",\"stored_address\":",
           name, pointer_address);
    if (stored_address == NULL)
        printf("null");
    else
        printf("\"%p\"", stored_address);
    puts("}");
    fflush(stdout);
}

#define OCHU_TRACE_POINTER(p) \
    ochu_trace_pointer(#p, (const void *)&(p), (const void *)(p))

static void ochu_trace_lamp(const char *phase, int *lamp,
                            int **caller_pointer)
{
    printf("{\"event\":\"lamp\",\"phase\":\"%s\","
           "\"object_address\":\"%p\",\"value\":%d,"
           "\"pointer_address\":\"%p\",\"stored_address\":\"%p\"}\n",
           phase, (void *)lamp, *lamp, (void *)caller_pointer,
           (void *)*caller_pointer);
    fflush(stdout);
}
'''

MAIN = r'''
int main(int argc, char **argv)
{
    if (argc != 2) return 2;
    char *end = NULL;
    long initial = strtol(argv[1], &end, 10);
    if (*end != '\0' || initial < -1000000 || initial > 1000000)
        return 2;
    int lamp_charge = (int)initial;
    int *caller_target = &lamp_charge;
    ochu_trace_lamp("before", &lamp_charge, &caller_target);
    charge(caller_target);
    ochu_trace_lamp("after", &lamp_charge, &caller_target);
    return 0;
}
'''


def process(command: list[str], directory: Path, timeout: float) -> dict:
    """Kill a timed-out process group; store output in size-checked temp files.

    This is NOT a security boundary. A hostile program can act as this user.
    """
    env = os.environ.copy()
    # Leak scanning requires process introspection unavailable in some hosted
    # development environments. Address/undefined-behavior checks still run.
    env["ASAN_OPTIONS"] = "detect_leaks=0:halt_on_error=1"
    env["UBSAN_OPTIONS"] = "halt_on_error=1:print_stacktrace=1"
    with tempfile.TemporaryFile() as out, tempfile.TemporaryFile() as err:
        child = subprocess.Popen(
            command, cwd=directory, env=env, stdin=subprocess.DEVNULL,
            stdout=out, stderr=err,
            start_new_session=os.name != "nt",
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0,
        )
        timed_out = False
        limit_hit = False
        deadline = time.monotonic() + timeout
        while child.poll() is None:
            if os.fstat(out.fileno()).st_size > MAX_OUTPUT or os.fstat(err.fileno()).st_size > MAX_OUTPUT:
                limit_hit = True
                break
            if time.monotonic() >= deadline:
                timed_out = True
                break
            time.sleep(0.01)
        # Clean up descendants too, including after the parent has exited.
        if os.name == "nt":
            if child.poll() is None:
                subprocess.run(["taskkill", "/PID", str(child.pid), "/T", "/F"],
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=5)
        else:
            try:
                os.killpg(child.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        child.wait()
        out.seek(0, os.SEEK_END)
        out_size = out.tell()
        err.seek(0, os.SEEK_END)
        err_size = err.tell()
        out.seek(0)
        err.seek(0)
        return {
            "returncode": child.returncode,
            "timed_out": timed_out,
            "stdout": out.read(MAX_OUTPUT).decode("utf-8", errors="replace"),
            "stderr": err.read(MAX_OUTPUT).decode("utf-8", errors="replace"),
            "output_truncated": limit_hit or out_size > MAX_OUTPUT or err_size > MAX_OUTPUT,
        }


def events_from(stdout: str) -> list[dict]:
    events = []
    for line in stdout.splitlines():
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            events.append(value)
    return events


def evaluate(source: str, compiler: str = "gcc", timeout: float = 2.0,
             demo: bool = False, sanitize: bool | None = None) -> dict:
    resolved_compiler = shutil.which(compiler)
    if resolved_compiler is None:
        return {"status": "compiler_unavailable", "compiler": compiler}
    report = {"compiler": resolved_compiler, "mode": "trusted_local_native_c"}
    with tempfile.TemporaryDirectory(prefix="ochu-c-") as temporary:
        directory = Path(temporary)
        program = directory / "program.c"
        binary = directory / ("program.exe" if os.name == "nt" else "program")
        program.write_text(source if demo else TRACE_HEADER + source + MAIN)
        flags = ["-std=c11", "-Wall", "-Wextra", "-Wpedantic", "-O0", "-g"]
        use_sanitizers = platform.system() == "Linux" if sanitize is None else sanitize
        if use_sanitizers:
            flags += ["-fsanitize=address,undefined", "-fno-omit-frame-pointer",
                      "-fno-pie", "-no-pie"]
        report["sanitizers"] = use_sanitizers
        compiled = process([resolved_compiler, *flags, str(program), "-o",
                            str(binary)], directory, 10.0)
        report["compile_diagnostics"] = compiled["stderr"]
        if compiled["output_truncated"]:
            return {**report, "status": "output_limit"}
        if compiled["timed_out"]:
            return {**report, "status": "compile_timeout"}
        if compiled["returncode"] != 0:
            return {**report, "status": "compile_error"}
        if demo:
            execution = process([str(binary)], directory, timeout)
            status = ("timeout" if execution["timed_out"] else
                      "output_limit" if execution["output_truncated"] else
                      "runtime_error" if execution["returncode"] != 0 else "passed")
            return {**report, "status": status,
                    "events": events_from(execution["stdout"]),
                    "runtime_diagnostics": execution["stderr"]}
        cases = []
        for initial in CASES:
            execution = process([str(binary), str(initial)], directory, timeout)
            events = events_from(execution["stdout"])
            final = next((e.get("value") for e in reversed(events)
                          if e.get("event") == "lamp" and
                          e.get("phase") == "after"), None)
            status = ("timeout" if execution["timed_out"] else
                      "output_limit" if execution["output_truncated"] else
                      "runtime_error" if execution["returncode"] != 0 else
                      "passed" if final == initial + 20 else "wrong_result")
            cases.append({"initial": initial, "expected": initial + 20,
                          "observed": final, "status": status, "events": events,
                          "runtime_diagnostics": execution["stderr"]})
            if status in ("timeout", "runtime_error", "output_limit"):
                break
        return {**report, "status": "passed" if len(cases) == len(CASES) and
                all(c["status"] == "passed" for c in cases) else "failed",
                "cases": cases}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", nargs="?", type=Path)
    parser.add_argument("--demo", action="store_true")
    parser.add_argument("--compiler", default="gcc")
    args = parser.parse_args()
    if args.demo:
        source = (ROOT / "examples" / "heap_lifecycle.c").read_text()
    elif args.source:
        source = args.source.read_text()
    else:
        parser.error("provide a trusted C source file, or use --demo")
    report = evaluate(source, compiler=args.compiler, demo=args.demo)
    print(json.dumps(report, indent=2))
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
