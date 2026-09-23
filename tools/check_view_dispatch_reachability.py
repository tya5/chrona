"""Keep declared View values connected to their Layout dispatches."""
from __future__ import annotations

import ast
import sys
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "schemas" / "view-v0.9.schema.yaml"

# Each entry is a closed author-facing dispatch family.  The checker proves
# both doors of the pipeline: the engine compares the value, and View admits it.
DISPATCHES = {
    ROOT / "src/chrona/presentation/layout/labels.py": {"inside"},
    ROOT / "src/chrona/presentation/layout/axis.py": {
        "short-month", "long-month", "numeric-month", "short-month-year",
        "long-month-year", "numeric-year-month", "quarter", "year-quarter", "quarter-year",
    },
}


def enum_values(value: object) -> set[str]:
    if isinstance(value, dict):
        found = set(value.get("enum", ())) if isinstance(value.get("enum"), list) else set()
        return found | set().union(*(enum_values(item) for item in value.values()))
    if isinstance(value, list):
        return set().union(*(enum_values(item) for item in value))
    return set()


def literals(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    return {node.value for node in ast.walk(tree) if isinstance(node, ast.Constant) and isinstance(node.value, str)}


def main() -> int:
    declared = enum_values(yaml.safe_load(SCHEMA.read_text(encoding="utf-8")))
    failures = []
    for path, values in DISPATCHES.items():
        missing_engine = sorted(values - literals(path))
        missing_schema = sorted(values - declared)
        failures.extend(f"dispatcher missing literal: {path.relative_to(ROOT)}:{value}" for value in missing_engine)
        failures.extend(f"View schema missing enum: {value}" for value in missing_schema)
    for failure in failures:
        print(failure)
    if failures:
        return 1
    print(f"{sum(map(len, DISPATCHES.values()))} View dispatch values have schema ingress")
    return 0


if __name__ == "__main__":
    sys.exit(main())
