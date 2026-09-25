"""Synchronize one provider descriptor into one declared Render Context."""
from __future__ import annotations

import argparse
from copy import deepcopy
from pathlib import Path
import re

import yaml

from chrona.resources import safe_load


class FontClosureSyncError(ValueError):
    """The requested Context/provider synchronization is unsafe."""


def _load(path: Path) -> dict:
    value = safe_load(path.read_bytes())
    if not isinstance(value, dict):
        raise FontClosureSyncError("E_FONT_CLOSURE_SYNC_SCHEMA")
    return value


def synchronize(descriptor_path: Path, context_path: Path) -> None:
    descriptor, context = _load(descriptor_path), _load(context_path)
    assets = descriptor.get("assets")
    environment = context.get("body", {}).get("environment")
    if descriptor.get("algorithm") != "declared-metrics-v3" or not isinstance(assets, list) or not isinstance(environment, dict):
        raise FontClosureSyncError("E_FONT_CLOSURE_SYNC_SCHEMA")
    current = environment.get("fontMetrics")
    if not isinstance(current, dict) or current.get("algorithm") != "declared-metrics-v3":
        raise FontClosureSyncError("E_FONT_CLOSURE_SYNC_SCHEMA")
    expected = {(item.get("family"), item.get("weight")) for item in assets if isinstance(item, dict)}
    current_assets = [item for item in current.get("assets", ()) if isinstance(item, dict)]
    actual = {(item.get("family"), item.get("weight")) for item in current_assets}
    # A provider may add a newly declared face.  Existing Context assets must
    # still be an exact non-empty subset; replacement may only extend the
    # closed descriptor, never drop or rewrite an unknown face.
    if not expected or not actual:
        raise FontClosureSyncError("E_FONT_CLOSURE_SYNC_TARGET")
    replacement_descriptor = deepcopy(descriptor)
    replacement_descriptor["assets"].extend(
        deepcopy(item) for item in current_assets if (item.get("family"), item.get("weight")) not in expected)
    replacement_descriptor["assets"].sort(key=lambda item: (str(item.get("family")), int(item.get("weight", 0))))
    descriptor_text = yaml.safe_dump(replacement_descriptor, sort_keys=False, allow_unicode=True).rstrip().splitlines()
    replacement = "    fontMetrics:\n" + "\n".join("      " + line if line else line for line in descriptor_text)
    source = context_path.read_text(encoding="utf-8")
    updated, count = re.subn(r"(?ms)^    fontMetrics:\n.*?(?=^    [A-Za-z]|\Z)", replacement + "\n", source, count=1)
    if count != 1:
        raise FontClosureSyncError("E_FONT_CLOSURE_SYNC_TARGET")
    context_path.write_text(updated, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("descriptor", type=Path)
    parser.add_argument("context", type=Path)
    args = parser.parse_args()
    synchronize(args.descriptor, args.context)


if __name__ == "__main__":
    main()
