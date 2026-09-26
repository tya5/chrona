#!/usr/bin/env python3
"""Generate/check the public audit of the bundled axis vocabulary catalog."""
from __future__ import annotations

import argparse
from pathlib import Path

from chrona.presentation.model.axis_names import MONTH_FORMS, _month_components, axis_name_catalog


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "docs/diagnostics/axis-name-tables.md"


def render_audit() -> str:
    lines = ["# Axis Name Tables", "", "Generated from the validated wheel-owned `axis-name-tables-v0.1.yaml` catalog.", "",
             "A coincidence is declared for every month in which two distinct forms produce identical text.", ""]
    for table_id, table in axis_name_catalog().items():
        lines.extend((f"## `{table_id}`", "", "| Month form | January 2026 |", "| --- | --- |"))
        components = _month_components(table, 1)
        for form in MONTH_FORMS:
            lines.append(f"| `{form}` | {table.format(form, components)} |")
        lines.extend(("", "| Selected alias | Canonical form | Coincident months |",
                      "| --- | --- | --- |"))
        if table.coincidences:
            for item in table.coincidences:
                months = ", ".join(str(month) for month in item.months)
                lines.append(f"| `{item.alias}` | `{item.canonical}` | {months} |")
        else:
            lines.append("| — | — | — |")
        lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--write", action="store_true")
    args = parser.parse_args()
    expected = render_audit()
    if args.check:
        if not OUTPUT.is_file() or OUTPUT.read_text(encoding="utf-8") != expected:
            print("E_AXIS_NAME_TABLE_AUDIT")
            return 1
        print("Axis name tables: PASS")
        return 0
    OUTPUT.write_text(expected, encoding="utf-8")
    print(f"Axis name tables: wrote {OUTPUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
