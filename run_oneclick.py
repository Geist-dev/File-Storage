"""Compatibility launcher. Prefer `bash start.sh` or the README's manual steps."""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if __name__ == '__main__':
    if sys.platform == 'win32':
        raise SystemExit('Use Git Bash: bash start.sh, or follow the PowerShell steps in README.md.')
    raise SystemExit(subprocess.call(['bash', str(ROOT / 'start.sh')]))
