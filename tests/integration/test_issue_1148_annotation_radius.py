"""Synthetic Layout evidence for physical annotation corner-radius tokens (#1148)."""
import pytest

from tests.support import annotation_kinds as ak
from tests.support import synthetic_review as sr


def _render(tmp_path, *, radius, outline=None):
    tmp_path.mkdir(parents=True, exist_ok=True)
    source = ak.project(("note",), text="A short synthetic note with enough words to measure.")
    parts = sr.bundle()
    ak.with_view_notes(parts, source, connector="tail" if outline == "balloon" else "none")
    theme = parts["theme"]["body"]
    theme["values"]["physical-radius"] = {"type": "radius", "value": radius}
    theme["roles"]["annotation-note-box"]["cornerRadius"] = "physical-radius"
    if outline is not None:
        container = {"outline": outline, "cornerRadius": 0.2}
        if outline == "balloon":
            container["tailBaseEm"] = 0.6
        theme["values"]["physical-radius-container"] = {
            "type": "annotationContainer", "value": container,
        }
        theme["roles"]["annotation-note-box"]["annotationContainer"] = "physical-radius-container"
    return sr.render(tmp_path, source, presentation=parts)


@pytest.mark.parametrize("outline", [None, "rectangle"])
def test_annotation_radius_token_overrides_legacy_and_resolves_on_the_painted_box(tmp_path, outline):
    rendered = _render(tmp_path, radius=5, outline=outline)
    box = next(item for item in rendered.surface.primitives if item.scene_id.startswith("annotation-box:"))
    text = next(item for item in rendered.surface.primitives if item.scene_id.startswith("annotation-text:"))

    assert box.kind == "Rect"
    assert box.corner_radius == 5
    assert text.bounds[0] - box.bounds[0] >= 5 * (1 - 1 / 2**0.5) - 0.05
    assert text.bounds[1] - box.bounds[1] >= 5 * (1 - 1 / 2**0.5) - 0.05


def test_balloon_radius_token_changes_the_completed_tail_outline(tmp_path):
    square = _render(tmp_path / "square", radius=0, outline="balloon")
    rounded = _render(tmp_path / "rounded", radius=6, outline="balloon")
    square_box = next(item for item in square.surface.primitives if item.scene_id.startswith("annotation-box:"))
    square_text = next(item for item in square.surface.primitives if item.scene_id.startswith("annotation-text:"))
    rendered = rounded
    box = next(item for item in rendered.surface.primitives if item.scene_id.startswith("annotation-box:"))
    text = next(item for item in rendered.surface.primitives if item.scene_id.startswith("annotation-text:"))
    assert box.kind.value == "Symbol"
    assert box.symbol is not None and box.symbol.outline
    assert box.symbol.outline != square_box.symbol.outline
    assert text.bounds[0] - box.bounds[0] > square_text.bounds[0] - square_box.bounds[0]


def test_capsule_fill_radius_keeps_wrapped_text_inside_the_final_corner(tmp_path):
    from tests.integration.test_note_inline_size import _prims

    tmp_path.mkdir(parents=True, exist_ok=True)
    parts = sr.bundle()
    sr.with_note_rail(parts, 80)
    theme = parts["theme"]["body"]
    theme["values"]["physical-radius"] = {"type": "radius", "value": "capsule"}
    theme["values"]["physical-radius-container"] = {
        "type": "annotationContainer",
        "value": {"outline": "rectangle", "cornerRadius": 0, "inlineSize": "fill"},
    }
    theme["roles"]["annotation-note-box"].update(
        cornerRadius="physical-radius", annotationContainer="physical-radius-container")
    source = sr.chain_project()
    candidate = sr.candidate("rail", region={"kind": "slot", "source": "annotations"},
                             search_kind="row-aligned", connector="leader")
    sr.add_notes(source, parts["view"], ["g0-t1", "g1-t2", "g2-t1"], [candidate], words=12)
    rendered = sr.render(tmp_path, source, presentation=parts)
    boxes = _prims(rendered, "annotation-box")
    texts = _prims(rendered, "annotation-text")
    clearance = 1 - 1 / 2**0.5

    assert boxes
    for note, box in boxes.items():
        text = texts[note]
        radius = min(box.bounds[2], box.bounds[3]) / 2
        assert box.corner_radius == pytest.approx(radius)
        assert text.bounds[0] - box.bounds[0] >= clearance * radius - 0.05
