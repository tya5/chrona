#!/usr/bin/env python3
"""Reject a semantic-registry entry without a production lookup path."""
from __future__ import annotations

import argparse
import ast
from pathlib import Path

from chrona.presentation.model.semantic_registry import semantic_ids


def reachable_semantic_ids(root: Path) -> frozenset[str]:
    """Return registry identifiers carried by Layout/Scene production code.

    A direct ``semantic_binding("...")`` call and a completed placement's
    semantic-id field are both lookup paths.  We deliberately inspect syntax,
    rather than execute composition, so a forgotten binding fails even when a
    corpus does not select its optional feature.
    """
    declared = set(semantic_ids())
    found: set[str] = set()
    semantic_factories: set[str] = set()
    for package in (root / "src/chrona/presentation/layout", root / "src/chrona/presentation/scene"):
        for path in package.rglob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            found.update(
                node.value for node in ast.walk(tree)
                if isinstance(node, ast.Constant) and isinstance(node.value, str) and node.value in declared
            )
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom) and node.module == "chrona.presentation.model.semantic_registry":
                    semantic_factories.update(alias.asname or alias.name for alias in node.names if alias.name != "semantic_binding")
    registry = ast.parse((root / "src/chrona/presentation/model/semantic_registry.py").read_text(encoding="utf-8"))
    for node in registry.body:
        if isinstance(node, ast.FunctionDef) and node.name in semantic_factories:
            found.update(
                value.value for value in ast.walk(node)
                if isinstance(value, ast.Constant) and isinstance(value.value, str) and value.value in declared
            )
    return frozenset(found)


def missing_semantic_ids(root: Path) -> tuple[str, ...]:
    return tuple(identifier for identifier in semantic_ids() if identifier not in reachable_semantic_ids(root))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("."))
    args = parser.parse_args()
    missing = missing_semantic_ids(args.root.resolve())
    if missing:
        raise SystemExit("E_SEMANTIC_REGISTRY_UNREACHABLE:" + ",".join(missing))


if __name__ == "__main__":
    main()
