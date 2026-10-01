#!/usr/bin/env bash
# doctor.sh — kept so existing instructions still work. The checks live in doctor.py, which runs
# the same on macOS, Windows (Git Bash, the shell Claude Code uses there) and Linux.
# Picks the repo's .venv Python when there is one, else the first real Python on PATH
# (on Windows "python3" is often the Microsoft Store stub, which exits non-zero and is skipped).
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/../../../../.." && pwd)"
for PY in "$ROOT/.venv/bin/python" "$ROOT/.venv/Scripts/python.exe" python3 python py; do
  if "$PY" -c "import sys; sys.exit(0 if sys.version_info >= (3, 8) else 1)" >/dev/null 2>&1; then
    cd "$ROOT" && exec "$PY" "$HERE/doctor.py" "$@"
  fi
done
echo "No working Python found. Windows: winget install Python.Python.3.12   macOS: brew install python@3.12" >&2
exit 1
