"""Synthetic box-border fixtures for the #1049 rules.

A Project with notes goes through the packaged `executive-light` bundle with a note rail; the note box role declares an
`annotationContainer.border` and the ink roles it needs. Nothing here reads `examples/`.
"""
from __future__ import annotations

from typing import Any, Iterable, Mapping

from tests.support import annotation_kinds as ak
from tests.support import synthetic_review as sr

RAIL = 300
TARGETS = ["g0-t1", "g1-t2", "g2-t1"]
SIDES = ("start", "end", "top", "bottom")
INSET = {"top": 0.5, "right": 1.0, "bottom": 0.7, "left": 2.0}
INKS = {"start": "accent", "end": "text", "top": "surface", "bottom": "accent"}


def rail_candidate() -> dict[str, Any]:
    return sr.candidate("rail", region={"kind": "slot", "source": "annotations"}, search_kind="row-aligned",
                        connector="leader")


def with_border(parts: dict[str, dict[str, Any]], border: Mapping[str, Any] | None, *, inset: Mapping[str, float] | None = None,
                outline: str = "rectangle", radius: float = 0, ink_roles: Iterable[str] = SIDES,
                extra: Mapping[str, Any] | None = None, kind_ink: bool = False) -> None:
    """Declare the note box container (with its border) and the per-side ink roles (and the kind accent ink role)."""
    theme = parts["theme"]["body"]
    value: dict[str, Any] = {"outline": outline, "cornerRadius": radius, **(extra or {})}
    if border is not None:
        value["border"] = {side: dict(entry) if isinstance(entry, Mapping) else entry for side, entry in border.items()}
    if inset is not None:
        value["contentInsetEm"] = dict(inset)
    if outline == "balloon":
        value["tailBaseEm"] = 0.6
    theme["values"]["border-container"] = {"type": "annotationContainer", "value": value}
    theme["roles"].setdefault("annotation-note-box", {})["annotationContainer"] = "border-container"
    for side in ink_roles:
        theme["roles"][f"annotation-border-{side}"] = {}
        theme["colorBindings"][f"annotation-border-{side}.fill"] = INKS[side]
    if kind_ink:
        theme["roles"]["annotation-kind-accent"] = {}
        theme["colorBindings"]["annotation-kind-accent.fill"] = "accent"


def render_notes(tmp_path: Any, border: Mapping[str, Any] | None, *, name: str = "r", words: int = 3, rail: int = RAIL,
                 candidates: list[Any] | None = None, texts: Iterable[str] = (), configure: Any = None, **kwargs: Any) -> Any:
    """Three notes in the rail through a Theme that declares `border`."""
    directory = tmp_path / name
    directory.mkdir()
    parts = sr.bundle()
    sr.with_note_rail(parts, rail)
    with_border(parts, border, **kwargs)
    if configure is not None:
        configure(parts)
    source = sr.chain_project()
    ids = sr.add_notes(source, parts["view"], TARGETS, candidates or [rail_candidate()], words=words)
    for note_id, text in zip(ids, texts, strict=False):
        source["annotations"][note_id]["text"] = text
    return sr.render(directory, source, presentation=parts)


def prims(rendered: Any, prefix: str) -> dict[str, Any]:
    """Scene primitives whose id starts with `prefix:`, by the remainder of the id."""
    return {item.scene_id.split(":", 1)[1]: item for item in rendered.surface.primitives
            if item.scene_id.startswith(prefix + ":")}


def boxes(rendered: Any) -> dict[str, Any]:
    return prims(rendered, "annotation-box")


def strips(rendered: Any, note: str = "note-0") -> dict[str, Any]:
    """The border strips of one note by side."""
    return {key.split(":", 1)[1]: item for key, item in prims(rendered, "annotation-border").items()
            if key.startswith(note + ":")}


def points(item: Any) -> list[tuple[float, float]]:
    """The corners of a polygon Symbol primitive (the closing point dropped), or of a Rect."""
    if item.kind.value == "Rect":
        x, y, w, h = item.bounds
        return [(x, y), (x + w, y), (x + w, y + h), (x, y + h)]
    return [command.points[0] for command in item.symbol.outline[:-1]]


render_kind = ak.render
