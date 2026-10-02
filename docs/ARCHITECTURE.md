# Local-first architecture

The browser renders story, mission console and memory lens. Python’s standard library serves local assets and calls GCC. Each player uses their own computer; no shared compiler host or remote execution queue is required. GitHub distributes the source and future release packages.

## Request boundary

The service binds to IPv4 loopback on an OS-assigned port. A random session path protects assets and saved progress. Compilation/saving require the correct Host, same-origin Origin, session header and JSON content type. There is no CORS permission for other websites. An explicit asset allowlist excludes source, saves and story spoilers. This prevents incidental exposure; it is not a defense against another process already running as the user.

One attempt runs at a time per launcher. The editor disables duplicate submissions and displays errors. Requests carry at most 16 KiB of C source. Compilation times out after 10 seconds and each execution after 2 seconds. Output is polled against a 64 KiB limit; it can temporarily exceed the cap between polling intervals. The returned output is truncated. POSIX process groups are cleaned up; Windows uses taskkill for a running timed-out process tree. Windows/macOS behavior still needs native testing.

C runs with the player’s permissions. Timeouts, session checks and sanitizers do not sandbox arbitrary C. This implementation is for trusted local learning code. A public execution service would require an independent isolation design.

## Evaluation and memory

The first quest accepts a complete `void charge(int *target)` function; parameter names and equivalent C syntax can vary. It runs with initial values 0, 40 and 75 and expects increases of 20. It does not compare the source text with one answer.

The harness explicitly logs the original integer and caller pointer before and after the learner function. `OCHU_TRACE_POINTER(p)` is available for learner-inserted pointer traces. This is instrumentation at selected locations, not an arbitrary C debugger or an automatic step trace.

Learner stdout shares the trace channel. Consequently forged trace events can fool the check. The game is practice, not a secure assessment system. A future evaluator can use an independent result channel and stronger behavioral tests if grading becomes a requirement.

Linux defaults to ASan/UBSan; plain compilation is used elsewhere or with `--no-sanitizers`. The startup smoke check validates basic compilation and execution. It does not guarantee sanitizer availability. Full compiler diagnostics appear in the console.

## Persistence and expansion

A bounded JSON journal containing the current scene and C source is written atomically in the user’s home folder. It survives different localhost ports, unlike origin-specific browser storage. Failed writes are visible. It contains no accounts, analytics or network synchronization.

Next refactor: scene and quest definitions into content files, a small quest registry with distinct harnesses, and separate save migrations. Only one pointer quest is currently connected to the UI. The heap example demonstrates malloc/realloc/free but is not yet a playable quest.
