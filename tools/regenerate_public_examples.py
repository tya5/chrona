#!/usr/bin/env python3
"""Regenerate or verify every committed public materializer in one bounded batch."""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from tempfile import TemporaryDirectory

from chrona.resources import safe_load
from tools.materialize_example import materialize


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    parser.add_argument("--jobs", type=int, default=4)
    args = parser.parse_args()
    if args.jobs < 1:
        parser.error("--jobs must be positive")
    targets = tuple((manifest, str(slide["id"]))
                    for manifest in sorted((ROOT / "examples").glob("*/manifest.yaml"))
                    for slide in safe_load(manifest.read_bytes())["slides"])
    with TemporaryDirectory(prefix="chrona-public-batch-") as temporary:
        root = Path(temporary)
        def run(target: tuple[Path, str]) -> None:
            manifest, slide_id = target
            materialize(manifest, slide_id, root / manifest.parent.name / slide_id, write=args.write)
        with ThreadPoolExecutor(max_workers=args.jobs) as executor:
            tuple(executor.map(run, targets))
    print(f"Public materializers: {'regenerated' if args.write else 'PASS'} ({len(targets)} slides)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
