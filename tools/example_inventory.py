"""Validate public corpus metadata and documentation references."""
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import yaml


class ExampleInventoryError(ValueError):
    """A corpus declaration or documentation reference is invalid."""


def _load(path: Path) -> Any:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def corpus(root: Path) -> dict[tuple[str, str], dict[str, Any]]:
    entries: dict[tuple[str, str], dict[str, Any]] = {}
    for manifest_path in sorted((root / "examples").glob("*/manifest.yaml")):
        manifest = _load(manifest_path)
        if not isinstance(manifest, dict) or manifest.get("role") != "regression-corpus":
            raise ExampleInventoryError(f"E_EXAMPLE_CORPUS_ROLE:{manifest_path.relative_to(root)}")
        identifier = manifest.get("id")
        slides = manifest.get("slides")
        if not isinstance(identifier, str) or not isinstance(slides, list):
            raise ExampleInventoryError(f"E_EXAMPLE_CORPUS_FORMAT:{manifest_path.relative_to(root)}")
        for slide in slides:
            if not isinstance(slide, dict) or not isinstance(slide.get("id"), str) or not isinstance(slide.get("evidence"), str) or not slide["evidence"].strip():
                raise ExampleInventoryError(f"E_EXAMPLE_SLIDE:{manifest_path.relative_to(root)}")
            key = (identifier, slide["id"])
            if key in entries:
                raise ExampleInventoryError(f"E_EXAMPLE_SLIDE_DUPLICATE:{identifier}:{slide['id']}")
            entries[key] = {"manifest": manifest_path.relative_to(root).as_posix(), "evidence": slide["evidence"]}
    return entries


def validate_catalog(path: Path, corpus_entries: dict[tuple[str, str], dict[str, Any]]) -> int:
    value = _load(path)
    if not isinstance(value, dict) or value.get("version") != "chrona/example-catalog/v0.1" or not isinstance(value.get("entries"), list):
        raise ExampleInventoryError(f"E_EXAMPLE_CATALOG_FORMAT:{path}")
    for entry in value["entries"]:
        if not isinstance(entry, dict) or not isinstance(entry.get("corpus"), str) or not isinstance(entry.get("slide"), str):
            raise ExampleInventoryError(f"E_EXAMPLE_CATALOG_ENTRY:{path}")
        if (entry["corpus"], entry["slide"]) not in corpus_entries:
            raise ExampleInventoryError(f"E_EXAMPLE_CATALOG_REFERENCE:{path}:{entry['corpus']}:{entry['slide']}")
    return len(value["entries"])


def validate(root: Path) -> tuple[int, int, int]:
    entries = corpus(root)
    curriculum = validate_catalog(root / "docs/guides/example-curriculum.yaml", entries)
    gallery = validate_catalog(root / "docs/gallery/example-gallery.yaml", entries)
    return len(entries), curriculum, gallery


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("."))
    args = parser.parse_args()
    slides, curriculum, gallery = validate(args.root)
    print(f"Example inventory: PASS ({slides} corpus slides, {curriculum} curriculum links, {gallery} gallery links)")


if __name__ == "__main__":
    main()
