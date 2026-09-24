#!/usr/bin/env python3
"""Require the packaged init template to match its corpus source exactly."""
from __future__ import annotations

from pathlib import Path


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    source, packaged = root / "examples" / "halcyon-1", root / "src" / "chrona" / "resources" / "examples" / "halcyon-1"
    source_files = {path.relative_to(source) for path in source.rglob("*") if path.is_file()}
    packaged_files = {path.relative_to(packaged) for path in packaged.rglob("*") if path.is_file()}
    different = sorted(source_files ^ packaged_files)
    different.extend(sorted(path for path in source_files & packaged_files if (source / path).read_bytes() != (packaged / path).read_bytes()))
    if different:
        raise SystemExit("E_INIT_TEMPLATE_STALE\n" + "\n".join(path.as_posix() for path in different))


if __name__ == "__main__":
    main()
