"""Standalone adapter for the public example materialization use case."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from chrona.usecases.materialize import copy_context_closure, materialize as _materialize
from chrona.usecases.failure_report import report_failure


_copy_context_closure = copy_context_closure


def materialize(manifest_path: Path, slide_id: str, output: Path, *, write: bool) -> None:
    """Delegate selection, copying and rendering to one application owner."""
    _materialize(manifest_path, slide_id, output, write=write)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest")
    parser.add_argument("--slide", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    try:
        materialize(Path(args.manifest), args.slide, Path(args.output), write=args.write)
    except Exception as error:
        report = report_failure(error)
        print(json.dumps(report.payload(), ensure_ascii=False))
        raise SystemExit(report.exit_code)


if __name__ == "__main__":
    main()
