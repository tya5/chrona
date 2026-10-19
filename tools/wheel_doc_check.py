#!/usr/bin/env python3
"""Run the documented commands against a built wheel in a fresh virtual environment (#1301).

The repository check (`check_documented_commands.py --check --execute`) runs the editable install next to a clone, so a
command that reads `examples/` passes there and fails for a user who ran `pip install`. This script builds the user's
situation: a new venv, the wheel plus its `render` extra and nothing else (no `-e`; `packages/chrona-fonts-noto-cjk` only where a guide declares the `cjk-font` prerequisite),
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
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.check_documented_commands import discover_prerequisites  # noqa: E402

# The documented setup for each `<!-- chrona:doc-check prerequisite: NAME -->` marker (#1724). The product bundles no
# font (#1281), so a guide that renders Japanese tells the reader to install a CJK font or the optional provider; the
# check follows the second route, which is the same on every OS, in the clean venv.
PREREQUISITES: dict[str, tuple[str, ...]] = {
    "cjk-font": ("packages/chrona-fonts-noto-cjk",),
}


def prerequisite_installs(root: Path, names: frozenset[str]) -> list[list[str]]:
    """The `pip install` argument lists for the declared prerequisites; an unknown name is an error, never ignored."""
    unknown = sorted(names - PREREQUISITES.keys())
    if unknown:
        raise SystemExit(f"E_WHEEL_DOC_CHECK_PREREQUISITE_UNKNOWN: {', '.join(unknown)}")
    return [["install", "--quiet", *(str(root / package) for package in PREREQUISITES[name])] for name in sorted(names)]


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
        for install in prerequisite_installs(ROOT, discover_prerequisites(ROOT)):
            subprocess.run([python, "-m", "pip", *install], check=True)
        subprocess.run([python, str(ROOT / "tools" / "check_documented_commands.py"), "--root", str(ROOT),
                        "--check", "--execute", "--wheel"], check=True)


if __name__ == "__main__":
    main()
