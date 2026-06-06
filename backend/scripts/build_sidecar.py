from __future__ import annotations

import argparse
import hashlib
import os
import shutil
import subprocess
import time
import tomllib
import venv
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
PYPROJECT_PATH = BACKEND_DIR / "pyproject.toml"
VENV_DIR = BACKEND_DIR / ".venv-sidecar"
STAMP_PATH = VENV_DIR / ".requirements-sha256"
SIDECAR_ENTRY = BACKEND_DIR / "run_sidecar.py"
SIDECAR_NAME = "mercury-backend.exe" if os.name == "nt" else "mercury-backend"


def main() -> None:
    args = parse_args()
    requirements = load_requirements()
    requirements_hash = compute_requirements_hash(requirements)

    ensure_venv()
    ensure_dependencies(requirements, requirements_hash)
    build_binary(args.output_dir)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir")
    return parser.parse_args()


def load_requirements() -> list[str]:
    config = tomllib.loads(PYPROJECT_PATH.read_text(encoding="utf-8"))
    dependencies = list(config["project"]["dependencies"])
    dependencies.extend(config.get("dependency-groups", {}).get("desktop", []))
    return dependencies


def compute_requirements_hash(requirements: list[str]) -> str:
    joined = "\n".join(requirements).encode("utf-8")
    return hashlib.sha256(joined).hexdigest()


def ensure_venv() -> None:
    if VENV_DIR.exists():
        return
    venv.EnvBuilder(with_pip=True).create(VENV_DIR)


def ensure_dependencies(requirements: list[str], requirements_hash: str) -> None:
    if STAMP_PATH.exists() and STAMP_PATH.read_text(encoding="utf-8") == requirements_hash:
        return

    python = venv_python()
    run(
        [
            python,
            "-m",
            "pip",
            "install",
            "--disable-pip-version-check",
            "--index-url",
            "https://pypi.org/simple",
            "--trusted-host",
            "pypi.org",
            "--trusted-host",
            "files.pythonhosted.org",
            *requirements,
        ]
    )
    STAMP_PATH.write_text(requirements_hash, encoding="utf-8")


def build_binary(output_dir: str) -> None:
    dist_dir = BACKEND_DIR / "dist"
    build_dir = BACKEND_DIR / "build"
    spec_path = BACKEND_DIR / "mercury-backend.spec"

    shutil.rmtree(dist_dir, ignore_errors=True)
    shutil.rmtree(build_dir, ignore_errors=True)
    spec_path.unlink(missing_ok=True)

    run(
        [
            venv_python(),
            "-m",
            "PyInstaller",
            "--noconfirm",
            "--clean",
            # --onedir (not --onefile): a one-file binary re-extracts its whole
            # Python runtime to a temp dir on EVERY launch, which made cold
            # startup blow past the desktop shell's health-check window. onedir
            # keeps the runtime unpacked next to the executable, so startup is
            # near-instant and reliable. Output: dist/mercury-backend/ holding
            # the `mercury-backend` executable plus an `_internal/` folder.
            "--onedir",
            "--name",
            "mercury-backend",
            str(SIDECAR_ENTRY),
        ]
    )

    if output_dir:
        source_binary = dist_dir / SIDECAR_NAME
        destination_dir = Path(output_dir)
        destination_dir.mkdir(parents=True, exist_ok=True)
        destination_binary = destination_dir / SIDECAR_NAME
        replace_with_retry(source_binary, destination_binary)


def run(command: list[str]) -> None:
    env = os.environ.copy()
    env["PYTHONNOUSERSITE"] = "1"
    for key in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy", "all_proxy"):
        env.pop(key, None)
    subprocess.run(command, cwd=BACKEND_DIR, check=True, env=env)


def venv_python() -> str:
    if os.name == "nt":
        return str(VENV_DIR / "Scripts" / "python.exe")
    return str(VENV_DIR / "bin" / "python")


def replace_with_retry(source_binary: Path, destination_binary: Path) -> None:
    temp_binary = destination_binary.with_suffix(destination_binary.suffix + ".tmp")

    for attempt in range(10):
        try:
            temp_binary.unlink(missing_ok=True)
            shutil.copy2(source_binary, temp_binary)
            os.replace(temp_binary, destination_binary)
            return
        except PermissionError:
            temp_binary.unlink(missing_ok=True)
            if attempt == 9:
                raise
            time.sleep(0.5)


if __name__ == "__main__":
    try:
        main()
    except subprocess.CalledProcessError as error:
        raise SystemExit(error.returncode) from error
