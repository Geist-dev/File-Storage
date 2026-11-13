#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"

# PYTHON may select a specific interpreter, e.g. PYTHON=python3.12 bash start.sh.
if [[ -n "${PYTHON:-}" ]]; then
  python_cmd="$PYTHON"
else
  python_cmd=""
  for candidate in python3.12 python3.13 python3.14 python3.11 python3 python; do
    if command -v "$candidate" >/dev/null 2>&1 && "$candidate" -c 'import sys; raise SystemExit(not ((3, 11) <= sys.version_info[:2] <= (3, 14)))' 2>/dev/null; then
      python_cmd="$candidate"
      break
    fi
  done
fi
if [[ -z "$python_cmd" ]]; then
  echo 'Install Python 3.11–3.14 (including venv), then run bash start.sh again.' >&2
  exit 1
fi
"$python_cmd" -c 'import sys; raise SystemExit(not ((3, 11) <= sys.version_info[:2] <= (3, 14)))' || {
  echo 'Python 3.11–3.14 is required.' >&2; exit 1;
}
if [[ ! -d .venv ]]; then
  "$python_cmd" -m venv .venv
fi
if [[ -x .venv/bin/python ]]; then
  venv_python=.venv/bin/python
elif [[ -f .venv/Scripts/python.exe ]]; then
  venv_python=.venv/Scripts/python.exe
else
  echo 'Incomplete .venv. Rename it and retry.' >&2
  exit 1
fi
"$venv_python" -m pip install -r backend/requirements.txt
"$venv_python" scripts/setup_env.py
# exec forwards Ctrl+C and the server exit code without leaving child services.
exec "$venv_python" scripts/serve.py
