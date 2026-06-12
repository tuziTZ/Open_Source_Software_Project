from __future__ import annotations

import argparse
import subprocess
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
VENV_PY = BACKEND_DIR / ".venv" / "bin" / "python"


def run(cmd):
    subprocess.run(cmd, cwd=BACKEND_DIR, check=True)


def main():
    run(["uv", "sync", "--group", "desktop"])

    run([
        "uv", "run",
        "python", "-m", "PyInstaller",
        "--noconfirm",
        "--clean",
        "--onedir",
        "--name", "mercury-backend",
        "run_sidecar.py"
    ])



if __name__ == "__main__":
    main()