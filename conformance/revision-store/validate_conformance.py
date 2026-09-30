#!/usr/bin/env python3
"""Schema evidence for the three standard Revision Store adapter profiles."""
from pathlib import Path
import sys

import yaml

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))
from chrona.resources import validator_for_schema


def load(path: Path):
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def main() -> int:
    manifest = load(HERE / "conformance-v0.1.yaml")
    failures = []
    for case in manifest["cases"]:
        schema = load((HERE / case["schema"]).resolve())
        value = load(HERE / case["resource"])
        valid = not list(validator_for_schema(schema).iter_errors(value))
        if valid != case["valid"]:
            failures.append(case["id"])
    if failures:
        print("Revision Store conformance: FAIL " + ", ".join(failures), file=sys.stderr)
        return 1
    print("Revision Store conformance: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
