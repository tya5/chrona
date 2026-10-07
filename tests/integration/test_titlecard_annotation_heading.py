"""#1201 public-context evidence; synthetic PR-path twin: test_annotation_rail_overflow."""
from dataclasses import replace
from pathlib import Path
from xml.etree import ElementTree

import pytest

from chrona.presentation.contracts import freeze
from chrona.presentation.model.closure import resolve_render_context
from chrona.scheduling.scheduler import ReferenceScheduler
from chrona.usecases.materialize import _OverlayBuilder, copy_context_closure
from chrona.usecases.render_review import RenderRequest, render_review

pytestmark = pytest.mark.corpus
ROOT = Path(__file__).resolve().parents[2]


def _thaw(value):
    if hasattr(value, "items"):
        return {key: _thaw(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_thaw(item) for item in value]
    return value


@pytest.mark.parametrize("size", [15, 17, 22])
def test_titlecard_heading_size_completes_distinct_full_frames(tmp_path, size):
    example = ROOT / "examples/halcyon-1"
    snapshot = tmp_path / "snapshot"
    snapshot.mkdir()
    decoded = {}
    builder = _OverlayBuilder(tmp_path)
    reference, _ = copy_context_closure(
        example, example / "contexts/23-titlecard.yaml", snapshot,
        decoded_catalogs=decoded, overlay_builder=builder)
    overlay = builder.finish()
    closure = resolve_render_context(reference, overlay, decoded_resources=decoded)
    # Keep authored resources and their verified identities untouched. Only the
    # resolved Theme value is varied for this diagnostic/acceptance render.
    theme = _thaw(closure.resolved_theme.resolved_input)
    theme["body"]["values"]["size.annotation-heading"]["value"] = size
    closure = replace(closure, resolved_theme=replace(
        closure.resolved_theme, resolved_input=freeze(theme)))
    result = render_review(RenderRequest(
        closure, snapshot, ReferenceScheduler(), asset_resolver=overlay))
    boxes = [item for item in result.scene.surfaces[0].primitives
             if item.scene_id.startswith("annotation-box:")]
    assert len(boxes) == 3
    for index, left in enumerate(boxes):
        x, y, width, height = left.bounds
        for right in boxes[index + 1:]:
            rx, ry, rw, rh = right.bounds
            assert not (x < rx + rw and rx < x + width and y < ry + rh and ry < y + height)
    svg = ElementTree.fromstring(result.artifact.content)
    rendered = {item.attrib.get("data-scene-id"): item for item in svg.iter()}
    for box in boxes:
        actual = rendered[box.scene_id]
        assert tuple(float(actual.attrib[key]) for key in ("x", "y", "width", "height")) == pytest.approx(
            box.bounds, abs=0.001)
    headings = [item for item in result.scene.surfaces[0].primitives
                if item.scene_id.startswith("annotation-heading:")]
    assert len(headings) == 3
    for heading in headings:
        assert float(rendered[heading.scene_id].attrib["font-size"]) == size
    if size == 15:
        assert result.artifact.content == (example / "generated/23-titlecard.svg").read_bytes()
