# Install and play locally

Download the repository ZIP from GitHub and extract it before launching. Running directly inside an archive will not work.

## Linux

Install Python 3.10+ and GCC using your distribution’s package manager. On Ubuntu/Debian:

```bash
sudo apt update
sudo apt install python3 build-essential
```

From the extracted game folder:

```bash
bash play.sh
```

## Windows

Install Python 3.10 or newer from https://www.python.org/downloads/windows/ and enable **Add Python to PATH**. Install a Windows GCC toolchain, such as MSYS2: https://www.msys2.org/. Follow its installation instructions and install the UCRT64 GCC package in its UCRT64 terminal. Ensure the resulting compiler’s bin directory is on the Windows PATH so `gcc --version` works in a new Command Prompt.

Double-click **Play.bat**. The launcher tries `py -3` first and then `python`. If the dependency check fails, the window remains open with the error. A bundled `.exe` and compiler installer are future work. This version needs validation on Windows; it is not a verified Windows release.

## macOS

Requires Python 3.10+ and a C compiler. Apple’s command-line tools supply a `gcc` command backed by Clang; the simple C quest can also use `python3 launcher.py --compiler clang`. macOS has not been validated for this preview.

## Troubleshooting

- **GCC was not found:** install GCC, open a new shell and verify `gcc --version`.
- **Compiler cannot compile/run:** verify your toolchain installation and runtime libraries.
- **Sanitizer-related compilation error on Linux:** try `bash play.sh --no-sanitizers`.
- **Browser did not open:** copy the full URL printed by the launcher. Its port and session path change every launch.
- **Lost browser connection:** keep the launcher open. Restart it and open the newly printed URL.
- **Journal could not save:** check write access to your home folder. The editor reports saving failures; copy your code before closing.

Do not forward the local port to the internet. The game does not require incoming network access.
