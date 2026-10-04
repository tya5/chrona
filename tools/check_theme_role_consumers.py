#!/usr/bin/env python3
"""Fail when a Theme declares a role or colour binding that no render closure of the repository reads (#1117).

A Theme is shared by several Views, so a name unread by one closure is legitimate for another. A name is dead only
when every Render Context that uses the Theme (and, for a bundled preset, the bundle's own View, Layout Profile and
Detail Profile) leaves it unread. The test is the one the renderer reports at render time
(`chrona.presentation.model.theme_role_consumers`). A derived Theme (`extends`) is read through its base file.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
from pathlib import Path
import sys
from typing import Any, Iterable, Mapping

from chrona.presentation.model.theme_role_consumers import declared_role_pointers, unread_roles
from chrona.resources import safe_load

ROOT = Path(__file__).resolve().parents[1]
_THEME_KINDS = ("chrona/theme/v0.15",)
_DOCUMENT_KEYS = ("view", "layout", "detailProfile", "summaryProfile")


def _load(path: Path) -> Mapping[str, Any] | None:
    try:
        value = safe_load(path.read_bytes())
    except (OSError, ValueError):
        return None
    return value if isinstance(value, Mapping) else None


def _context_documents(example: Path, context: Mapping[str, Any]) -> tuple[Path | None, list[Any]]:
    body = context.get("body")
    if not isinstance(body, Mapping):
        return None, []
    theme = body.get("theme")
    theme_path = example / theme["address"] if isinstance(theme, Mapping) and isinstance(theme.get("address"), str) else None
    documents: list[Any] = []
    inputs = body.get("inputs") if isinstance(body.get("inputs"), Mapping) else {}
    for reference in (body.get("view"), body.get("layout"), inputs.get("detailProfile"), inputs.get("summaryProfile")):
        if isinstance(reference, Mapping) and isinstance(reference.get("address"), str):
            document = _load(example / reference["address"])
            if document is not None:
                documents.append(document)
    return theme_path, documents


def _closures(root: Path) -> Iterable[tuple[Path, list[Any]]]:
    for context_path in sorted(root.glob("examples/*/contexts/*.yaml")):
        context = _load(context_path)
        if context is None:
            continue
        theme_path, documents = _context_documents(context_path.parents[1], context)
        if theme_path is not None:
            yield theme_path, documents
    for bundle in sorted(root.glob("src/chrona/resources/presets/bundles/*")):
        documents = [document for name in ("view.yaml", "layout.yaml", "detail.yaml", "summary.yaml")
                     if (bundle / name).is_file() and (document := _load(bundle / name)) is not None]
        if (bundle / "theme.yaml").is_file():
            yield bundle / "theme.yaml", documents


def dead_declarations(root: Path = ROOT) -> tuple[str, ...]:
    """`path:role` for every role of a non-derived Theme that every closure using it leaves unread."""
    unread: dict[Path, list[set[str]]] = defaultdict(list)
    bodies: dict[Path, Mapping[str, Any]] = {}
    for theme_path, documents in _closures(root):
        theme = _load(theme_path)
        if theme is None or theme.get("version") not in _THEME_KINDS or not isinstance(theme.get("body"), Mapping):
            continue
        bodies[theme_path] = theme["body"]
        unread[theme_path].append(set(unread_roles(theme["body"], documents)))
    result: list[str] = []
    for theme_path, per_closure in sorted(unread.items()):
        dead = set.intersection(*per_closure) if per_closure else set()
        for role in sorted(dead & set(declared_role_pointers(bodies[theme_path]))):
            result.append(f"E_THEME_ROLE_UNREAD:{theme_path.relative_to(root).as_posix()}:{role}")
    return tuple(result)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=ROOT)
    arguments = parser.parse_args()
    findings = dead_declarations(arguments.root.resolve())
    for finding in findings:
        print(finding)
    if findings:
        return 1
    print("Theme role consumers: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
