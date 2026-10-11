"""#584 A584-3: the deterministic annotation tilt, rendered end to end.

A Theme `annotationContainer.tiltDegrees` cycle turns the notes by small, declared angles; Layout searches and
registers each note through the bounds of its rotated frame and rotates every element of the frame rigidly.
Synthetic Projects through the packaged `executive-light` bundle; no `examples/` input.
"""
from __future__ import annotations

from math import atan2, cos, degrees, radians, sin
from pathlib import Path

import pytest

from chrona.presentation.layout.annotation_tilt import nearest_boundary_point, rotate_point, rotated_extent
from chrona.presentation.renderers.v05_typeset import render_v05_tikz, render_v05_typst
from chrona.presentation.scene.contrast_policy import evaluate_scene_contrast
from chrona.presentation.scene.perceptibility import evaluate_scene_perceptibility
from chrona.presentation.scene.serialization import scene_document, serialize_scene
from tests.support import annotation_kinds as ak
from tests.support import synthetic_review as sr

PAD_INLINE, PAD_BLOCK = 0.6 * 16, 0.6 * 16 / 2
TEXT = 14
MATERIAL = next(parent for parent in Path(__file__).resolve().parents if (parent / "pyproject.toml").is_file()
                ) / "src/chrona/resources/icons/material-symbols-outline-rounded-v2026-09-22.yaml"


def _render(tmp_path, *, tilt=None, kinds=None, source=None, connector="none", mutate=None, rich=False, **theme):
    source = source or ak.project()
    parts = sr.bundle()
    ak.with_view_notes(parts, source, connector=connector)
    if kinds:
        ak.with_kind_theme(parts, **theme)
    if tilt is not None:
        ak.with_tilt(parts, tilt)
    if mutate is not None:
        mutate(parts)
    if rich:
        return ak.render(tmp_path, source, parts)
    return sr.render(tmp_path, source, presentation=parts)


def _sub(tmp_path, name):
    path = tmp_path / name
    path.mkdir()
    return path


def _by_id(rendered):
    return {item.scene_id: item for item in rendered.surface.primitives}


def _polygon(primitive):
    return [command.points[0] for command in primitive.symbol.outline[:4]]


def _axes(polygon):
    """The inline and block unit vectors of a rotated frame, from its first three corners."""
    (x0, y0), (x1, y1), (x2, y2) = polygon[0], polygon[1], polygon[2]
    inline = (x1 - x0, y1 - y0)
    length = (inline[0] ** 2 + inline[1] ** 2) ** 0.5
    u = (inline[0] / length, inline[1] / length)
    return u, (-u[1], u[0])


def test_an_absent_or_zero_cycle_changes_nothing(tmp_path):
    base = _render(_sub(tmp_path, "base"))
    zero = _render(_sub(tmp_path, "zero"), tilt=[0])
    assert list(zero.surface.primitives) == list(base.surface.primitives)
    assert zero.artifact.content == base.artifact.content
    assert all(item.kind.value == "Rect" for item in base.surface.primitives if item.scene_id.startswith("annotation-box:"))


def test_a_fixed_angle_tilts_every_note_box_and_text(tmp_path):
    rendered = _render(tmp_path, tilt=[4])
    ids = _by_id(rendered)
    for note in ("view-n0", "view-n1"):
        box, text = ids[f"annotation-box:{note}"], ids[f"annotation-text:{note}"]
        assert box.kind.value == "Symbol" and len(box.symbol.outline) == 5
        assert text.text_layout.orientation == "tilt" and text.text_layout.rotation_degrees == 4.0


def test_the_cycle_follows_the_views_declared_order_not_the_projects(tmp_path):
    source = ak.project(kinds=("risk", "note", "risk", "note"))

    def reversed_view(parts):
        parts["view"]["body"]["annotations"].reverse()

    rendered = _render(tmp_path, source=source, tilt=[1, 2, 3], mutate=reversed_view)
    ids = _by_id(rendered)
    order = ["view-n3", "view-n2", "view-n1", "view-n0"]  # the View's order after the reversal
    assert [ids[f"annotation-text:{note}"].text_layout.rotation_degrees for note in order] == [1.0, 2.0, 3.0, 1.0]


def test_an_alternation_and_a_negative_angle_turn_the_other_way(tmp_path):
    ids = _by_id(_render(tmp_path, tilt=[3, -3]))
    assert ids["annotation-text:view-n0"].text_layout.rotation_degrees == 3.0
    assert ids["annotation-text:view-n1"].text_layout.rotation_degrees == -3.0


def test_the_box_bounds_are_the_rotated_extent_of_the_untilted_frame(tmp_path):
    source = ak.project()
    plain = _by_id(_render(_sub(tmp_path, "plain"), source=source))
    tilted = _by_id(_render(_sub(tmp_path, "tilted"), source=source, tilt=[4, -3]))
    for note, angle in (("view-n0", 4.0), ("view-n1", -3.0)):
        width, height = rotated_extent(plain[f"annotation-box:{note}"].bounds[2], plain[f"annotation-box:{note}"].bounds[3], angle)
        assert tilted[f"annotation-box:{note}"].bounds[2:] == pytest.approx((width, height), abs=1e-3)


def test_tilted_notes_stay_apart_and_inside_the_plot(tmp_path):
    rendered = _render(_sub(tmp_path, "t"), source=ak.project(kinds=("risk", "note", "risk")), tilt=[5, -5])
    ids = _by_id(rendered)
    boxes = [ids[f"annotation-box:view-n{index}"].bounds for index in range(3)]
    for index, (x, y, w, h) in enumerate(boxes):
        for other in boxes[index + 1:]:
            ox, oy, ow, oh = other
            assert x + w <= ox + 1e-6 or ox + ow <= x + 1e-6 or y + h <= oy + 1e-6 or oy + oh <= y + 1e-6
    plot = next(slot for slot in rendered.surface.slots if slot.source == "timeline").bounds
    for x, y, w, h in boxes:
        assert x >= plot[0] - 1e-6 and y >= plot[1] - 1e-6 and x + w <= plot[0] + plot[2] + 1e-6 and y + h <= plot[1] + plot[3] + 1e-6


def test_the_body_text_is_rotated_rigidly_with_the_box(tmp_path):
    ids = _by_id(_render(tmp_path, tilt=[4, -3]))
    for note, angle in (("view-n0", 4.0), ("view-n1", -3.0)):
        polygon = _polygon(ids[f"annotation-box:{note}"])
        u, v = _axes(polygon)
        assert degrees(atan2(u[1], u[0])) == pytest.approx(angle, abs=1e-6)
        text = ids[f"annotation-text:{note}"]
        # The unrotated baseline starts at the frame's inline start, one text size below its block start.
        expected = (polygon[0][0] + v[0] * TEXT, polygon[0][1] + v[1] * TEXT)
        assert text.baseline == pytest.approx(expected, abs=1e-3)


def test_the_svg_rotates_the_text_about_its_baseline_start_and_draws_the_polygon(tmp_path):
    rendered = _render(tmp_path, tilt=[4])
    svg = rendered.artifact.content.decode()
    ids = _by_id(rendered)
    x, y = ids["annotation-text:view-n0"].baseline
    assert f'transform="rotate(4 {x:.3f}'.replace(".000", "") in svg or 'transform="rotate(4 ' in svg
    box = next(line for line in svg.splitlines() if 'data-scene-id="annotation-box:view-n0"' in line)
    assert "<path " in box and "<rect " not in box


def test_the_kind_frame_rotates_with_the_note(tmp_path):
    rendered = _render(tmp_path, kinds=True, tilt=[4, -3])
    ids = _by_id(rendered)
    for note, angle in (("view-n0", 4.0), ("view-n1", -3.0)):
        box, bar = _polygon(ids[f"annotation-box:{note}"]), _polygon(ids[f"annotation-kind-bar:{note}"])
        assert bar[0] == pytest.approx(box[0], abs=1e-3)  # the bar starts at the box's rotated top-left corner
        u, v = _axes(box)
        first = ids[f"annotation-kind-text:{note}:0"]
        expected = (bar[0][0] + u[0] * PAD_INLINE + v[0] * (PAD_BLOCK + 16), bar[0][1] + u[1] * PAD_INLINE + v[1] * (PAD_BLOCK + 16))
        assert first.baseline == pytest.approx(expected, abs=1e-3)
        assert first.text_layout.rotation_degrees == angle


def test_a_stamp_rotates_with_the_note(tmp_path):
    flat = _render(_sub(tmp_path, "flat"), kinds=True, stamp="end-top", rich=True)
    tilted = _render(_sub(tmp_path, "tilted"), kinds=True, stamp="end-top", tilt=[6], rich=True)

    def direction(rendered):
        part = next(item for item in rendered.surface.primitives if item.scene_id == "annotation-kind-stamp:view-n0:part1")
        (x0, y0), (x1, y1) = part.symbol.outline[0].points[0], part.symbol.outline[1].points[-1]
        return atan2(y1 - y0, x1 - x0)

    assert degrees(direction(tilted) - direction(flat)) == pytest.approx(6.0, abs=1e-3)
    box = _by_id(tilted)["annotation-box:view-n0"].bounds
    for item in tilted.surface.primitives:
        if item.scene_id.startswith("annotation-kind-stamp:view-n0"):
            x, y, w, h = item.bounds
            assert x >= box[0] - 1e-6 and y >= box[1] - 1e-6 and x + w <= box[0] + box[2] + 1e-6 and y + h <= box[1] + box[3] + 1e-6


def test_a_leader_goes_on_to_the_edge_of_the_rotated_box(tmp_path):
    rendered = _render(tmp_path, tilt=[8, -8], connector="leader")
    ids = _by_id(rendered)
    leaders = [item for item in rendered.surface.primitives if item.scene_id.startswith("annotation-leader:")]
    assert leaders
    for leader in leaders:
        note = leader.scene_id.removeprefix("annotation-leader:")
        polygon = _polygon(ids[f"annotation-box:{note}"])
        end = leader.points[-1] if leader.points else leader.path_commands[-1].points[-1]
        assert nearest_boundary_point(polygon, end) == pytest.approx(end, abs=1e-6)  # the leader touches the paper
        x, y, w, h = ids[f"annotation-box:{note}"].bounds
        assert not (abs(end[0] - x) < 1e-6 or abs(end[0] - (x + w)) < 1e-6) or not (abs(end[1] - y) < 1e-6 or abs(end[1] - (y + h)) < 1e-6)


def test_label_visuals_on_a_tilted_note_are_rejected(tmp_path):
    source = ak.project()

    def parts_with(tilt):
        parts = sr.bundle()
        ak.with_view_notes(parts, source)
        parts["view"]["body"]["visuals"] = [{"target": {"kind": "annotation", "id": "view-n0"},
                                             "ref": "material:10k-outline-rounded", "decorative": True}]
        if tilt:
            ak.with_tilt(parts, [4])
        return parts

    with pytest.raises(Exception) as failure:
        ak.render(_sub(tmp_path, "tilted"), source, parts_with(True), catalogs=(MATERIAL,),
                  visual_profile="chrona-output/visual/v0.7-svg")
    assert "E_LAYOUT_ANNOTATION_TILT_VISUAL" in str(failure.value)
    # The same note without a tilt takes the visual, so the rejection is the tilt's and not the fixture's.
    flat = ak.render(_sub(tmp_path, "flat"), source, parts_with(False), catalogs=(MATERIAL,),
                     visual_profile="chrona-output/visual/v0.7-svg")
    assert any(item.scene_id.startswith("visual:annotation-text:view-n0") for item in flat.surface.primitives)


def test_a_tilted_scene_is_written_as_v07_and_an_untilted_one_stays_v06(tmp_path):
    tilted = _render(_sub(tmp_path, "tilted"), tilt=[4])
    plain = _render(_sub(tmp_path, "plain"))
    assert scene_document(tilted.scene)["version"] == "chrona/scene/v0.7"
    assert scene_document(plain.scene)["version"] == "chrona/scene/v0.6"
    serialize_scene(tilted.scene)  # validates against the schema
    layouts = [item["textLayout"] for item in scene_document(tilted.scene)["surfaces"][0]["primitives"] if "textLayout" in item]
    assert {item["rotationDegrees"] for item in layouts if item["orientation"] == "tilt"} == {4.0}


def test_rendering_twice_gives_the_same_bytes(tmp_path):
    first = _render(_sub(tmp_path, "a"), kinds=True, tilt=[4, -3])
    second = _render(_sub(tmp_path, "b"), kinds=True, tilt=[4, -3])
    assert first.artifact.content == second.artifact.content


def test_tikz_draws_the_rotation_and_typst_draws_the_symbol_box_as_a_curve(tmp_path):
    surface = _render(tmp_path, tilt=[4]).surface
    tikz = render_v05_tikz(surface)
    assert "rotate=4" in tikz
    typst = render_v05_typst(surface)  # the tilted box is a closed Symbol outline (#1308)
    assert "#curve(" in typst and "curve.close()" in typst


def test_the_contrast_gate_judges_the_rotated_text_on_its_box(tmp_path):
    rendered = _render(tmp_path, tilt=[4, -3])
    document = scene_document(rendered.scene)
    findings = {item.primitive_id: item for item in evaluate_scene_contrast(document) if item.visual_role == "annotation-note-text"}
    assert set(findings) == {"annotation-text:view-n0", "annotation-text:view-n1"}
    assert all(item.severity == "info" and item.ground_id.startswith("annotation-box:") for item in findings.values())
    # Independent rail statuses are free text, not prose on a rotated box.
    statuses = {item.primitive_id: item for item in evaluate_scene_contrast(document)
                if item.purpose == "annotation-list-text"}
    assert set(statuses) == {"annotation-status:view-n0", "annotation-status:view-n1"}
    assert all(item.severity == "info" and not item.ground_id.startswith("annotation-box:")
               for item in statuses.values())
    for primitive in document["surfaces"][0]["primitives"]:
        if primitive["id"] == "annotation-box:view-n0":
            primitive["paint"]["fill"] = "#1B2536"  # as dark as the note ink
    errors = [item for item in evaluate_scene_contrast(document)
              if item.visual_role == "annotation-note-text" and item.severity == "error"]
    assert [item.primitive_id for item in errors] == ["annotation-text:view-n0"]
    assert errors[0].code == "E_SCENE_STATE_TEXT_CONTRAST"


def test_the_contrast_gate_judges_a_rotated_header_on_its_bar(tmp_path):
    document = scene_document(_render(tmp_path, kinds=True, tilt=[4, -3]).scene)
    labels = [item for item in evaluate_scene_contrast(document) if item.visual_role == "annotation-kind-label"]
    assert {item.ground_id for item in labels} == {"annotation-kind-bar:view-n0", "annotation-kind-bar:view-n1"}
    for primitive in document["surfaces"][0]["primitives"]:
        if primitive["id"] == "annotation-kind-bar:view-n1":
            primitive["paint"]["fill"] = "#F2F2F2"
    failing = {item.primitive_id for item in evaluate_scene_contrast(document)
               if item.visual_role == "annotation-kind-label" and item.severity == "error"}
    assert failing == {"annotation-kind-text:view-n1:0"}


def test_the_stacked_lines_of_one_tilted_note_are_not_an_intersection(tmp_path):
    document = scene_document(_render(tmp_path, kinds=True, tilt=[6, -6]).scene)
    findings = evaluate_scene_perceptibility(document)
    assert not [item for item in findings if item.code == "E_SCENE_TEXT_INTERSECTION"]


def test_a_note_that_tilts_and_one_that_does_not_can_share_a_slide(tmp_path):
    rendered = _render(tmp_path, tilt=[0, 5])
    ids = _by_id(rendered)
    assert ids["annotation-box:view-n0"].kind.value == "Rect" and ids["annotation-text:view-n0"].text_layout.orientation == "horizontal"
    assert ids["annotation-box:view-n1"].kind.value == "Symbol" and ids["annotation-text:view-n1"].text_layout.rotation_degrees == 5.0


def test_rotate_point_agrees_with_the_layout_rotation_of_a_baseline(tmp_path):
    ids = _by_id(_render(tmp_path, tilt=[4]))
    polygon = _polygon(ids["annotation-box:view-n0"])
    centre = (sum(x for x, _ in polygon) / 4, sum(y for _, y in polygon) / 4)
    x0, y0, width, height = ids["annotation-box:view-n0"].bounds
    angle = radians(4.0)
    frame_w = (ids["annotation-box:view-n0"].bounds[2] * cos(angle) - ids["annotation-box:view-n0"].bounds[3] * sin(angle)) / cos(2 * angle)
    frame_h = (ids["annotation-box:view-n0"].bounds[3] * cos(angle) - ids["annotation-box:view-n0"].bounds[2] * sin(angle)) / cos(2 * angle)
    unrotated_baseline = (centre[0] - frame_w / 2, centre[1] - frame_h / 2 + TEXT)
    assert ids["annotation-text:view-n0"].baseline == pytest.approx(rotate_point(unrotated_baseline, centre, 4.0), abs=1e-3)
