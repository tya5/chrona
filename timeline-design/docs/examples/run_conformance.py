#!/usr/bin/env python3
"""Run Core and Presentation conformance entry points."""
from pathlib import Path
import subprocess, sys

ROOT = Path(__file__).resolve().parent
COMMANDS = [
    [sys.executable, str(ROOT / "validate_conformance.py")],
    [sys.executable, str(ROOT / "presentation" / "validate_conformance.py")],
]
for command in COMMANDS:
    result = subprocess.run(command, check=False)
    if result.returncode:
        raise SystemExit(result.returncode)
print("Chrona conformance: PASS")
