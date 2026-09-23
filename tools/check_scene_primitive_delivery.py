"""Reject ScenePrimitive fields that product code never consumes.

Scene is the renderer-neutral hand-off.  A field retained there must be read by
at least one presentation consumer; otherwise it is a misleading capability,
not inspectable evidence.
"""
from __future__ import annotations

import ast
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "src" / "chrona" / "presentation"
MODEL = SOURCE / "scene" / "model.py"


def scene_primitive_fields() -> set[str]:
    tree = ast.parse(MODEL.read_text(encoding="utf-8"), filename=str(MODEL))
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == "ScenePrimitive":
            return {item.target.id for item in node.body if isinstance(item, ast.AnnAssign)
                    and isinstance(item.target, ast.Name)}
    raise ValueError("ScenePrimitive dataclass not found")


def consumed_attributes() -> set[str]:
    consumed: set[str] = set()
    for path in SOURCE.rglob("*.py"):
        if path == MODEL:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        consumed.update(node.attr for node in ast.walk(tree)
                        if isinstance(node, ast.Attribute) and isinstance(node.ctx, ast.Load))
    return consumed


def main() -> int:
    unused = sorted(scene_primitive_fields() - consumed_attributes())
    for field in unused:
        print(f"undelivered ScenePrimitive field: {field}")
    if unused:
        print("Every ScenePrimitive field must have a presentation consumer; delete stale metadata instead of allowlisting it.")
        return 1
    print(f"{len(scene_primitive_fields())} ScenePrimitive fields consumed, none stale")
    return 0


if __name__ == "__main__":
    sys.exit(main())
