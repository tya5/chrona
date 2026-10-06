from datetime import date

import pytest

from chrona.presentation.scene.serialization import scene_document, validate_scene_document
from tests.support import synthetic_review as sr


@pytest.mark.parametrize("alignment", ["inside", "outside"])
@pytest.mark.parametrize("point", [False, True])
def test_authored_alignment_reaches_scene_with_completed_geometry(tmp_path, alignment, point):
    parts = sr.bundle()
    parts["theme"]["body"]["roles"]["planned"]["strokeAlign"] = alignment
    objects = {"a": sr.point("a", date(2026, 2, 2)) if point else sr.span("a", date(2026, 2, 2), 30)}
    if point:
        objects["window"] = sr.span("window", date(2026, 2, 1), 30)
    source = sr.project(objects)
    rendered = sr.render(tmp_path, source, presentation=parts)
    marks = [node for node in rendered.surface.primitives if node.scene_id.startswith("planned:") and node.source_ref == "a"]
    assert len(marks) == 1
    mark = marks[0]
    assert mark.stroke_clip is not None
    assert mark.stroke_clip.outside == (alignment == "outside")
    assert mark.paint.stroke_width == mark.stroke_clip.stroke_width == 2
    assert bool(mark.stroke_clip.outline) == point
    document = scene_document(rendered.scene)
    validate_scene_document(document)
    assert 'mask-type="luminance"' in rendered.artifact.content.decode()


@pytest.mark.parametrize("point", [False, True])
def test_center_declaration_is_byte_identical_and_inside_keeps_declared_bounds(tmp_path, point):
    parts = sr.bundle()
    objects = {"a": sr.point("a", date(2026, 2, 2)) if point else sr.span("a", date(2026, 2, 2), 30),
               "window": sr.span("window", date(2026, 2, 1), 30)}
    source = sr.project(objects)
    for name in ("baseline", "center", "inside"):
        (tmp_path / name).mkdir()
    baseline = sr.render(tmp_path / "baseline", source, presentation=parts)
    parts["theme"]["body"]["roles"]["planned"]["strokeAlign"] = "center"
    centered = sr.render(tmp_path / "center", source, presentation=parts)
    assert centered.artifact.content == baseline.artifact.content
    # The authored Theme identity changes; completed geometry and paint do not.
    assert scene_document(centered.scene)["surfaces"] == scene_document(baseline.scene)["surfaces"]
    parts["theme"]["body"]["roles"]["planned"]["strokeAlign"] = "inside"
    aligned = sr.render(tmp_path / "inside", source, presentation=parts)
    old = {node.scene_id: node for node in baseline.surface.primitives}
    assert [node.scene_id for node in aligned.surface.primitives] == list(old)
    for node in aligned.surface.primitives:
        assert node.bounds == old[node.scene_id].bounds
