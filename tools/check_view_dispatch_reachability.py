"""Keep declared View values connected to their Layout dispatches."""
from __future__ import annotations

import ast
import sys
from pathlib import Path

from chrona.resources import safe_load


ROOT = Path(__file__).resolve().parents[1]
INVENTORY = ROOT / "schemas" / "schema-inventory-v0.1.yaml"


def live_view_schema() -> Path:
    """The View schema the inventory marks live, so a View bump cannot leave this check on a stale pin."""
    entries = [entry for entry in safe_load(INVENTORY.read_bytes())["schemas"]
               if entry["kind"] == "view" and entry["state"] == "live"]
    if len(entries) != 1:
        raise SystemExit(f"expected exactly one live View schema in the inventory, found {len(entries)}")
    return ROOT / "schemas" / entries[0]["file"]


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
        # Dispatch values are strings; an enum may also list arrays (View v0.28 `rows.packing`), which do not hash.
        found = {item for item in value["enum"] if isinstance(item, str)} if isinstance(value.get("enum"), list) else set()
        return found | set().union(*(enum_values(item) for item in value.values()))
    if isinstance(value, list):
        return set().union(*(enum_values(item) for item in value))
    return set()


def literals(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    return {node.value for node in ast.walk(tree) if isinstance(node, ast.Constant) and isinstance(node.value, str)}


def main() -> int:
    declared = enum_values(safe_load(live_view_schema().read_bytes()))
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
