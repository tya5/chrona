#!/usr/bin/env python3
"""Schema evidence for the three standard Revision Store adapter profiles."""
from pathlib import Path
import sys

import yaml
from jsonschema import Draft202012Validator


HERE = Path(__file__).resolve().parent


def load(path: Path):
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def main() -> int:
    manifest = load(HERE / "conformance-v0.1.yaml")
    failures = []
    for case in manifest["cases"]:
        schema = load((HERE / case["schema"]).resolve())
        value = load(HERE / case["resource"])
        valid = not list(Draft202012Validator(schema).iter_errors(value))
        if valid != case["valid"]:
            failures.append(case["id"])
    if failures:
        print("Revision Store conformance: FAIL " + ", ".join(failures), file=sys.stderr)
        return 1
    print("Revision Store conformance: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
