# from __future__ import annotations
#
# import subprocess
# from pathlib import Path
#
# BACKEND_DIR = Path(__file__).resolve().parents[1]
# VENV_PY = BACKEND_DIR / ".venv" / "bin" / "python"
#
#
# def run(cmd):
#     subprocess.run(cmd, cwd=BACKEND_DIR, check=True)
#
#
# def main():
#     run(["uv", "sync", "--group", "desktop"])
#
#     run([
#         "uv", "run",
#         "python", "-m", "PyInstaller",
#         "--noconfirm",
#         "--clean",
#         "--onedir",
#         "--name", "mercury-backend",
#         "run_sidecar.py"
#     ])
#
#
#
# if __name__ == "__main__":
#     main()
from __future__ import annotations

import argparse
import hashlib
import os
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
PYPROJECT_PATH = BACKEND_DIR / "pyproject.toml"
SIDECAR_ENTRY = BACKEND_DIR / "run_sidecar.py"

DIST_DIR = BACKEND_DIR / "dist"
BUILD_DIR = BACKEND_DIR / "build"


def main():
    args = parse_args()

    requirements = load_requirements()

    install_dependencies(requirements)
    build_binary(args.output_dir)


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir")
    return parser.parse_args()


def load_requirements():
    cfg = tomllib.loads(PYPROJECT_PATH.read_text(encoding="utf-8"))
    deps = list(cfg["project"]["dependencies"])
    deps += cfg.get("dependency-groups", {}).get("desktop", [])
    return deps


def install_dependencies(requirements):
    subprocess.run(
        [sys.executable, "-m", "pip", "install", "--upgrade", "pip"],
        check=True,
    )

    subprocess.run(
        [sys.executable, "-m", "pip", "install", *requirements],
        check=True,
    )


def build_binary(output_dir: str | None):
    shutil.rmtree(DIST_DIR, ignore_errors=True)
    shutil.rmtree(BUILD_DIR, ignore_errors=True)

    subprocess.run(
        [
            sys.executable,
            "-m",
            "PyInstaller",
            "--noconfirm",
            "--clean",
            "--onedir",
            "--name",
            "mercury-backend",
            str(SIDECAR_ENTRY),
        ],
        check=True,
        cwd=BACKEND_DIR,
    )

    if output_dir:
        source = DIST_DIR / "mercury-backend"
        dest = Path(output_dir)
        dest.mkdir(parents=True, exist_ok=True)
        shutil.copytree(source, dest / "mercury-backend", dirs_exist_ok=True)


if __name__ == "__main__":
    main()
