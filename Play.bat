@echo off
cd /d "%~dp0"
where py >nul 2>nul
if not errorlevel 1 (
  py -3 launcher.py %*
  goto finished
)
where python >nul 2>nul
if not errorlevel 1 (
  python launcher.py %*
  goto finished
)
echo Python was not found. Install Python 3.10 or newer from python.org.
echo Enable "Add Python to PATH", then launch again.
:finished
pause
