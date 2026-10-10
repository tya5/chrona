"""Execute the literal CONTRIBUTING setup recipe, not a second CI recipe."""
from __future__ import annotations

from pathlib import Path
import re
import shlex
import subprocess
import sys


def setup_commands(document: str) -> tuple[tuple[str, ...], ...]:
    blocks = re.findall(r"<!-- contributor-setup -->\s*```bash\n(.*?)\n```", document, re.DOTALL)
    if len(blocks) != 1:
        raise ValueError("E_CONTRIBUTOR_SETUP: expected exactly one documented setup recipe")
    commands = tuple(tuple(shlex.split(line)) for line in blocks[0].splitlines() if line.strip())
    if not commands or any(not command for command in commands):
        raise ValueError("E_CONTRIBUTOR_SETUP: empty recipe")
    return commands


def run_setup(root: Path) -> None:
    if (root / ".venv").exists():
        raise ValueError("E_CONTRIBUTOR_SETUP: fresh checkout must not already contain .venv")
    for command in setup_commands((root / "CONTRIBUTING.md").read_text(encoding="utf-8")):
        # `python` denotes the Python selected by setup-python, never a shell.
        argv = (sys.executable, *command[1:]) if command[0] == "python" else command
        subprocess.run(argv, cwd=root, check=True)


if __name__ == "__main__":
    run_setup(Path(__file__).resolve().parents[1])
