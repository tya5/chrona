#!/usr/bin/env python3
"""Render read-only Markdown pages for the validated design gallery."""
from __future__ import annotations

import argparse
from collections import defaultdict
from pathlib import Path
import tempfile
from typing import Any, Mapping

from chrona.resources import safe_load
from tools.example_inventory import corpus, validate_design_gallery


def _load(path: Path) -> Mapping[str, Any]:
    value = safe_load(path.read_bytes())
    if not isinstance(value, Mapping):
        raise ValueError(f"E_DESIGN_GALLERY_FORMAT:{path}")
    return value


def _reference_diff(contexts: list[Mapping[str, Any]]) -> list[str]:
    keys = ("view", "theme", "colorScheme", "layout")
    result = []
    for key in keys:
        values = [str(context["body"][key]["id"]) for context in contexts]
        if len(set(values)) > 1:
            result.append(f"- `{key}`: " + " → ".join(f"`{value}`" for value in values))
    return result or ["- No presentation-reference difference (invalid gallery input)."]


def render(root: Path) -> dict[Path, str]:
    catalogue_path = root / "docs/gallery/example-gallery.yaml"
    entries = corpus(root)
    validate_design_gallery(catalogue_path, root, entries)
    catalogue = _load(catalogue_path)
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for entry in catalogue["entries"]:
        grouped[entry["comparison"]["set"]].append(entry)
    pages: dict[Path, str] = {}
    index = ["# Public Design Gallery", "", "Generated from declared corpus evidence; it is not a renderer or an authoring input.",
             "", "## Comparison sets", "", "| Question | Dimension | Peers |", "| --- | --- | --- |"]
    for set_id, set_entries in sorted(grouped.items()):
        comparison = set_entries[0]["comparison"]
        page = Path("docs/gallery/sets") / f"{set_id}.md"
        index.append(f"| [{comparison['axis']}](sets/{page.name}) | `{comparison['dimension']}` | {len(set_entries)} |")
        contexts = [_load(root / Path(entries[(entry["corpus"], entry["slide"])]["manifest"]).parent /
                          entries[(entry["corpus"], entry["slide"])]["context"]) for entry in set_entries]
        lines = [f"# {comparison['axis']}", "", f"Design Space dimension: `{comparison['dimension']}`.",
                 "", "## Peers", ""]
        for entry in set_entries:
            source = entries[(entry["corpus"], entry["slide"])]
            base = Path(source["manifest"]).parent
            image = Path("../../../") / base / source["expectedSvg"]
            context = Path("../../../") / base / source["context"]
            lines.extend([f"### {entry['narrative']['title']}", "", entry["narrative"]["purpose"], "",
                          f"![{entry['narrative']['title']}]({image.as_posix()})", "",
                          f"Corpus: `{entry['corpus']}` · slide: `{entry['slide']}` · [Context]({context.as_posix()})", ""])
        lines.extend(["## Presentation-reference diff", "", *_reference_diff(contexts), "",
                      "## Accessibility", ""])
        lines.extend(f"- {entry['narrative']['title']}: {entry['accessibility']['note']}" for entry in set_entries)
        lines.append("")
        pages[page] = "\n".join(lines)
    coverage = root / "docs/examples/corpus-coverage.md"
    index.extend(["", "## Coverage backlog", "", f"See [corpus coverage](../examples/{coverage.name}). Missing vocabulary is curation backlog, not a render gate.", ""])
    pages[Path("docs/gallery/README.md")] = "\n".join(index)
    return pages


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as temporary:
        temporary.write(content)
        temporary_path = Path(temporary.name)
    temporary_path.replace(path)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(); root = args.root.resolve()
    pages = render(root)
    stale = [path for path, content in pages.items() if not (root / path).is_file() or (root / path).read_text(encoding="utf-8") != content]
    if args.check:
        if stale: raise SystemExit("E_DESIGN_GALLERY_STALE")
        return
    for path, content in pages.items(): _write(root / path, content)


if __name__ == "__main__":
    main()
