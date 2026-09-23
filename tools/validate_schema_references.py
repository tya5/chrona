"""Check explicitly current contract declarations in normative specifications."""
from __future__ import annotations

import argparse
import re
from pathlib import Path

import yaml

from tools.schema_inventory import validate_inventory


class SchemaReferenceError(ValueError):
    pass


VERSION = re.compile(r"^\s*version:\s*([A-Za-z0-9_./-]+)\s*$")


def live_versions(schema_root: Path, inventory_path: Path) -> set[str]:
    values: set[str] = set()
    for entry in validate_inventory(schema_root, inventory_path):
        if entry["state"] != "live":
            continue
        schema = yaml.safe_load((schema_root / entry["file"]).read_text())
        const = schema.get("properties", {}).get("version", {}).get("const")
        if isinstance(const, str):
            values.add(const)
    return values


def validate_specifications(specification_root: Path, schema_root: Path, inventory_path: Path) -> None:
    live = live_versions(schema_root, inventory_path)
    for path in sorted(specification_root.glob("*.md")):
        lines = path.read_text().splitlines()
        for number, line in enumerate(lines):
            match = VERSION.match(line)
            if not match:
                continue
            marker = lines[number - 1].strip() if number else ""
            if marker == "# chrona-contract: historical":
                continue
            if marker != "# chrona-contract: current":
                raise SchemaReferenceError(f"E_SCHEMA_REFERENCE_UNCLASSIFIED:{path}:{number + 1}")
            if match.group(1) not in live:
                raise SchemaReferenceError(f"E_SCHEMA_REFERENCE_STALE:{path}:{number + 1}:{match.group(1)}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--specifications", type=Path, default=Path("docs/specification"))
    parser.add_argument("--schemas", type=Path, default=Path("schemas"))
    parser.add_argument("--inventory", type=Path, default=Path("schemas/schema-inventory-v0.1.yaml"))
    args = parser.parse_args()
    validate_specifications(args.specifications, args.schemas, args.inventory)


if __name__ == "__main__":
    main()
