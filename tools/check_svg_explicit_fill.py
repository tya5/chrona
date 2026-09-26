"""Reject implicit SVG fills in committed public drawable evidence."""
from __future__ import annotations

from pathlib import Path
from xml.etree import ElementTree


ROOT = Path(__file__).resolve().parents[1]
DRAWABLE_SHAPES = frozenset({"rect", "path", "line", "circle", "ellipse", "polygon", "polyline"})


def implicit_fills(svg: str) -> tuple[str, ...]:
    """Return drawable identifiers whose paint relies on SVG's black default."""
    root = ElementTree.fromstring(svg)
    missing: list[str] = []

    def visit(element: ElementTree.Element, *, in_clip: bool = False) -> None:
        name = element.tag.rsplit("}", 1)[-1]
        clipped = in_clip or name == "clipPath"
        if not clipped and name in DRAWABLE_SHAPES and "fill" not in element.attrib:
            missing.append(element.attrib.get("data-scene-id", name))
        for child in element:
            visit(child, in_clip=clipped)

    visit(root)
    return tuple(missing)


def main() -> int:
    paths = sorted((ROOT / "examples").glob("*/generated/*.svg"))
    if not paths:
        print("E_SVG_EVIDENCE_MISSING")
        return 1
    failures = [(path.relative_to(ROOT), item)
                for path in paths
                for item in implicit_fills(path.read_text(encoding="utf-8"))]
    for path, item in failures:
        print(f"E_SVG_IMPLICIT_FILL:{path}:{item}")
    if not failures:
        print(f"Explicit SVG fill: PASS ({len(paths)} public SVGs)")
    return int(bool(failures))


if __name__ == "__main__":
    raise SystemExit(main())
