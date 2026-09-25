"""Validate public corpus metadata and documentation references."""
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import yaml

from chrona.resources import safe_load


DIMENSION_OWNERS = {
    "content": frozenset({"view"}),
    "composition": frozenset({"layout"}),
    "visual-grammar": frozenset({"view"}),
    "appearance": frozenset({"theme", "colorScheme"}),
}
SUPPORT_OWNERS = frozenset({"layout", "theme"})
PRESENTATION_REFERENCES = ("view", "theme", "colorScheme", "layout")


class ExampleInventoryError(ValueError):
    """A corpus declaration or documentation reference is invalid."""


def _load(path: Path) -> Any:
    return safe_load(path.read_bytes())


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
            context = slide.get("context", manifest.get("context"))
            expected = slide.get("expectedSvg")
            if not isinstance(context, str) or not isinstance(expected, str):
                raise ExampleInventoryError(f"E_EXAMPLE_SLIDE:{manifest_path.relative_to(root)}")
            entries[key] = {"manifest": manifest_path.relative_to(root).as_posix(), "evidence": slide["evidence"],
                            "context": context, "expectedSvg": expected}
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


def validate_design_gallery(path: Path, root: Path, corpus_entries: dict[tuple[str, str], dict[str, Any]]) -> int:
    value = _load(path)
    if not isinstance(value, dict) or value.get("version") != "chrona/design-gallery/v0.2" or not isinstance(value.get("entries"), list):
        raise ExampleInventoryError(f"E_DESIGN_GALLERY_FORMAT:{path}")
    deferred = value.get("deferred", [])
    if (not isinstance(deferred, list) or any(not isinstance(item, dict) or not isinstance(item.get("id"), str)
            or ("dimension" in item and item["dimension"] not in DIMENSION_OWNERS)
            or not isinstance(item.get("blocker"), str) or not item["blocker"] for item in deferred)):
        raise ExampleInventoryError(f"E_DESIGN_GALLERY_DEFERRED:{path}")
    deferred_ids = [item["id"] for item in deferred]
    if len(deferred_ids) != len(set(deferred_ids)):
        raise ExampleInventoryError(f"E_DESIGN_GALLERY_DEFERRED:{path}")
    seen: set[str] = set(); pairs: dict[str, list[tuple[dict[str, Any], dict[str, Any]]]] = {}
    for entry in value["entries"]:
        if not isinstance(entry, dict) or not all(isinstance(entry.get(key), str) and entry[key] for key in ("id", "corpus", "slide")):
            raise ExampleInventoryError(f"E_DESIGN_GALLERY_ENTRY:{path}")
        if entry["id"] in seen or entry["id"] in deferred_ids: raise ExampleInventoryError(f"E_DESIGN_GALLERY_DUPLICATE:{entry['id']}")
        seen.add(entry["id"]); key = (entry["corpus"], entry["slide"])
        if key not in corpus_entries: raise ExampleInventoryError(f"E_DESIGN_GALLERY_REFERENCE:{entry['id']}")
        narrative, comparison, target, accessibility = (entry.get(name) for name in ("narrative", "comparison", "target", "accessibility"))
        if not isinstance(narrative, dict) or not all(isinstance(narrative.get(k), str) and narrative[k] for k in ("title", "audience", "purpose")):
            raise ExampleInventoryError(f"E_DESIGN_GALLERY_NARRATIVE:{entry['id']}")
        if not isinstance(comparison, dict) or not isinstance(comparison.get("set"), str) or not comparison["set"]:
            raise ExampleInventoryError(f"E_DESIGN_GALLERY_PAIR:{entry['id']}")
        if not isinstance(comparison.get("axis"), str) or not comparison["axis"]:
            raise ExampleInventoryError(f"E_DESIGN_GALLERY_AXIS:{entry['id']}")
        if comparison.get("dimension") not in DIMENSION_OWNERS:
            raise ExampleInventoryError(f"E_DESIGN_GALLERY_DIMENSION:{entry['id']}")
        supports = comparison.get("supports", [])
        if (not isinstance(supports, list) or supports != sorted(set(supports))
                or any(item not in SUPPORT_OWNERS for item in supports)
                or (supports and comparison["dimension"] != "content")):
            raise ExampleInventoryError(f"E_DESIGN_GALLERY_SUPPORT:{entry['id']}")
        if not isinstance(accessibility, dict) or not isinstance(accessibility.get("note"), str) or not accessibility["note"]:
            raise ExampleInventoryError(f"E_DESIGN_GALLERY_ACCESSIBILITY:{entry['id']}")
        context = _context(root, corpus_entries[key])
        evidence = root / Path(corpus_entries[key]["manifest"]).parent / corpus_entries[key]["expectedSvg"]
        if not evidence.is_file():
            raise ExampleInventoryError(f"E_DESIGN_GALLERY_EVIDENCE:{entry['id']}")
        actual_target = context["body"]["target"]
        if not isinstance(target, dict) or target.get("kind") != actual_target.get("kind") or not set(target.get("capabilities", [])).issubset(set(actual_target.get("capabilities", []))):
            raise ExampleInventoryError(f"E_DESIGN_GALLERY_TARGET:{entry['id']}")
        pairs.setdefault(comparison["set"], []).append((context, comparison))
    for pair, entries in pairs.items():
        contexts = [item[0] for item in entries]
        if len(contexts) < 2: raise ExampleInventoryError(f"E_DESIGN_GALLERY_UNPAIRED:{pair}")
        if len({item[1]["dimension"] for item in entries}) != 1:
            raise ExampleInventoryError(f"E_DESIGN_GALLERY_DIMENSION:{pair}")
        if len({item[1]["axis"] for item in entries}) != 1:
            raise ExampleInventoryError(f"E_DESIGN_GALLERY_AXIS:{pair}")
        if len({tuple(item[1].get("supports", [])) for item in entries}) != 1:
            raise ExampleInventoryError(f"E_DESIGN_GALLERY_SUPPORT:{pair}")
        bodies = [item["body"] for item in contexts]
        if len({_identity(body["project"]) for body in bodies}) != 1 or len({_identity(body.get("inputs", {}).get("actual")) for body in bodies}) != 1:
            raise ExampleInventoryError(f"E_DESIGN_GALLERY_SEMANTIC_MISMATCH:{pair}")
        if len({_identity(body.get("environment")) for body in bodies}) != 1:
            raise ExampleInventoryError(f"E_DESIGN_GALLERY_ENVIRONMENT_MISMATCH:{pair}")
        presentation = [{key: _identity(body[key]) for key in PRESENTATION_REFERENCES} for body in bodies]
        dimension = entries[0][1]["dimension"]
        owners = DIMENSION_OWNERS[dimension]
        supports = frozenset(entries[0][1].get("supports", []))
        changed = {key for key in PRESENTATION_REFERENCES if len({item[key] for item in presentation}) > 1}
        if not changed:
            raise ExampleInventoryError(f"E_DESIGN_GALLERY_PRESENTATION_EQUAL:{pair}")
        if not changed & owners:
            raise ExampleInventoryError(f"E_DESIGN_GALLERY_OWNER_UNCHANGED:{pair}")
        for reference in sorted(changed - owners - supports):
            raise ExampleInventoryError(f"E_DESIGN_GALLERY_AXIS_LEAK:{pair}:{reference}")
    return len(seen)


def _context(root: Path, entry: dict[str, Any]) -> dict[str, Any]:
    corpus = Path(entry["manifest"]).parent
    value = _load(root / corpus / entry["context"])
    if not isinstance(value, dict) or value.get("kind") != "render-context" or not isinstance(value.get("body"), dict):
        raise ExampleInventoryError("E_DESIGN_GALLERY_CONTEXT")
    return value


def _identity(value: Any) -> str:
    return yaml.safe_dump(value, sort_keys=True)


def validate(root: Path) -> tuple[int, int, int]:
    entries = corpus(root)
    curriculum = validate_catalog(root / "docs/guides/example-curriculum.yaml", entries)
    gallery = validate_design_gallery(root / "docs/gallery/example-gallery.yaml", root, entries)
    return len(entries), curriculum, gallery


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("."))
    args = parser.parse_args()
    slides, curriculum, gallery = validate(args.root)
    print(f"Example inventory: PASS ({slides} corpus slides, {curriculum} curriculum links, {gallery} gallery links)")


if __name__ == "__main__":
    main()
