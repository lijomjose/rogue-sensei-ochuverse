#!/usr/bin/env bash
set -e
cd -- "$(dirname -- "$0")"
if ! command -v python3 >/dev/null 2>&1; then
  echo "Python 3.10 or newer was not found. Install Python, then launch again."
  exit 1
fi
exec python3 launcher.py "$@"
