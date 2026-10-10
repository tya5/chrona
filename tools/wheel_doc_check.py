#!/usr/bin/env python3
"""Run the documented commands against a built wheel in a fresh virtual environment (#1301).

The repository check (`check_documented_commands.py --check --execute`) runs the editable install next to a clone, so a
command that reads `examples/` passes there and fails for a user who ran `pip install`. This script builds the user's
situation: a new venv, the wheel plus its `render` extra and nothing else (no `-e`, no `packages/chrona-fonts-noto-cjk`),
and an empty workspace. Commands marked `requires: clone` are skipped.

    python tools/wheel_doc_check.py dist/chrona-*.whl
"""
from __future__ import annotations

import argparse
import subprocess
import sys
import tempfile
import venv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def venv_python(directory: Path) -> Path:
    return directory / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("wheel", type=Path)
    args = parser.parse_args()
    wheel = args.wheel.resolve()
    with tempfile.TemporaryDirectory(prefix="chrona-wheel-doc-check-") as temporary:
        environment = Path(temporary) / "venv"
        venv.EnvBuilder(with_pip=True).create(environment)
        python = str(venv_python(environment))
        subprocess.run([python, "-m", "pip", "install", "--quiet", f"{wheel}[render]"], check=True)
        subprocess.run([python, str(ROOT / "tools" / "check_documented_commands.py"), "--root", str(ROOT),
                        "--check", "--execute", "--wheel"], check=True)


if __name__ == "__main__":
    main()
