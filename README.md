# Rogue Sensei · Ochuverse

An expanding, story-driven adventure where players learn data structures through C coding quests. The journey begins in Pointerra, then grows into other worlds and concepts.

## Play the development preview

Download this repository as a ZIP (Code → Download ZIP) and extract it, or clone it:

```bash
git clone https://github.com/lijomjose/rogue-sensei-ochuverse.git
cd rogue-sensei-ochuverse
bash play.sh
```

On Windows, double-click **Play.bat** in the extracted folder. Requires **Python 3.10+**, **GCC** and a modern browser. No pip packages, account or internet connection are needed after downloading and installing dependencies. See [installation instructions](docs/INSTALL.md).

The launcher checks the compiler and opens a browser. Keep the launcher window open while playing; Ctrl+C stops it. If the browser does not open, copy the printed URL. `python3 launcher.py --no-browser` also works.

## Playable now

An amnesiac traveller wakes alone in Pointerra. Inspect a beacon and write a real C pointer spell. GCC checks three starting charges; the memory lens shows the caller pointer’s own address, the address stored inside it, and the original integer before/after execution. Restoring the beacon opens the path toward a familiar stranger.

Code and progress save in `~/.rogue-sensei-ochuverse/pointerra.json`, surviving new local ports/sessions. This is an opening development slice, not the completed module. CSS scenery is temporary. Comic scrolls, established character art, allocation quests, the chapter ending and later worlds remain planned. There is no Windows `.exe` yet. Windows/macOS compatibility requires native validation.

## Development

```bash
python3 -m unittest discover -s tests -v
python3 runtime/runner.py runtime/examples/charge_correct.c
python3 runtime/runner.py --demo
```

Linux uses GCC ASan/UBSan by default. Other platforms currently use plain C compilation. If Linux GCC lacks sanitizer support, launch with `bash play.sh --no-sanitizers`; memory-error diagnostics will be unavailable. Leak checking is disabled in this early runtime.

- `game/`: offline interface.
- `launcher.py`, `play.sh`, `Play.bat`: dependency checks and launchers.
- `runtime/`: real C evaluation, traces and examples.
- `docs/`: installation, architecture, story bible and roadmap.
- `tests/`: compiler and local-service checks.

The service binds only to `127.0.0.1`, serves explicitly allowed game assets, and checks a private session for compilation requests. See [architecture and limitations](docs/ARCHITECTURE.md). C executes with your user’s permissions. Use your own lesson code; this is not a security sandbox or an adversarial grading service. Do not expose it as a public compiler server.

The existing MIT license is retained. Future third-party or separately licensed assets need their attribution and license recorded before inclusion.
