"""#584 A584-2: the annotation kind stamp (a catalogue glyph per kind in a reserved corner column), end to end.

A Project with Project annotations of two kinds goes through the packaged `executive-light` bundle and the
packaged `chrona-target-parts` catalogue (seal glyphs). No `examples/` input.
"""
from __future__ import annotations

from copy import deepcopy

import pytest

from chrona.presentation.scene.contrast_policy import evaluate_scene_contrast
from chrona.presentation.scene.serialization import scene_document
from tests.support import annotation_kinds as ak
from tests.support import synthetic_review as sr

LABEL, SECONDARY = 16 * 1.2, 11 * 1.2
TEXT = 14  # the note text size of the fixture Theme
SEAL_PARTS = {"view-n0": 7, "view-n1": 9}  # parts of seal-risk and seal-note


def _render(tmp_path, *, source=None, mutate=None, **theme):
    source = source or ak.project()
    parts = sr.bundle()
    ak.with_view_notes(parts, source)
    ak.with_kind_theme(parts, **theme)
    if mutate is not None:
        mutate(parts)
    return ak.render(tmp_path, source, parts)


def _sub(tmp_path, name):
    path = tmp_path / name
    path.mkdir()
    return path


def _by_id(rendered):
    return {item.scene_id: item for item in rendered.surface.primitives}


def _stamp(rendered, note):
    return [item for item in rendered.surface.primitives if item.scene_id.startswith(f"annotation-kind-stamp:{note}")]


def test_a_kind_without_a_stamp_declaration_renders_as_the_header_alone(tmp_path):
    header = _render(_sub(tmp_path, "header"))
    stamped = _render(_sub(tmp_path, "stamped"), stamp="end-top", stamps={})
    assert list(stamped.surface.primitives) == list(header.surface.primitives)


def test_without_a_stamp_role_a_declared_glyph_is_absent(tmp_path):
    header = _render(_sub(tmp_path, "header"))

    def declare_only(parts):
        for kind, glyph in ak.STAMPS.items():
            parts["theme"]["body"]["annotationKinds"][kind]["stamp"] = glyph

    declared = _render(_sub(tmp_path, "declared"), mutate=declare_only)
    assert list(declared.surface.primitives) == list(header.surface.primitives)


def test_each_kind_draws_its_own_glyph_part_by_part_in_its_kind_colour(tmp_path):
    rendered = _render(tmp_path, stamp="end-top")
    for note, count in SEAL_PARTS.items():
        parts = _stamp(rendered, note)
        assert len(parts) == count
        assert all(item.visual_role == "annotation-kind-stamp" and item.kind == "Symbol" for item in parts)
        color = ak.KIND_COLORS["kind-alert" if note == "view-n0" else "kind-report"]
        assert {item.paint.stroke for item in parts} == {color} and {item.paint.fill for item in parts} == {None}
        assert all(item.paint.stroke_width and item.paint.stroke_width > 0 for item in parts)


@pytest.mark.parametrize("corner", ["start-top", "end-top", "start-bottom", "end-bottom"])
def test_the_stamp_stands_in_its_corner_column_and_never_overlaps_the_text(tmp_path, corner):
    rendered = _render(tmp_path, stamp=corner, stamp_size=2.0)
    ids = _by_id(rendered)
    box = ids["annotation-box:view-n0"]
    x, y, w, h = box.bounds
    stamp = _stamp(rendered, "view-n0")[0]
    sx, sy, sw, sh = stamp.bounds
    assert sh == pytest.approx(2.0 * TEXT) and sw == pytest.approx(sh)  # a square glyph at the declared size
    assert (sx == pytest.approx(x)) == corner.startswith("start")
    assert (sx + sw == pytest.approx(x + w)) == corner.startswith("end")
    assert (sy == pytest.approx(y)) == corner.endswith("top")
    assert (sy + sh == pytest.approx(y + h)) == corner.endswith("bottom")
    for name in ("annotation-text:view-n0", "annotation-kind-text:view-n0:0", "annotation-kind-text:view-n0:1"):
        tx, _, tw, _ = ids[name].bounds
        assert tx + tw <= sx + 1e-6 or tx >= sx + sw - 1e-6, name  # disjoint inline ranges


def test_the_glyph_keeps_its_own_aspect_and_the_column_follows_it(tmp_path):
    rendered = _render(tmp_path, stamp="end-top", stamp_size=1.5, stamps={"risk": "chrona-target-parts:hazard-tab"})
    ids = _by_id(rendered)
    box, bar = ids["annotation-box:view-n0"], ids["annotation-kind-bar:view-n0"]
    stamp = _stamp(rendered, "view-n0")[0]
    assert stamp.bounds[3] == pytest.approx(1.5 * TEXT)
    assert stamp.bounds[2] == pytest.approx(1.5 * TEXT * 56 / 24)  # the hazard tab is a 56 x 24 glyph
    assert bar.bounds[2] == pytest.approx(box.bounds[2] - stamp.bounds[2] - 0.5 * TEXT)


def test_the_column_narrows_the_bar_and_the_text_and_widens_the_box(tmp_path):
    source = ak.project()
    plain = _by_id(_render(_sub(tmp_path, "plain"), source=source))
    stamped = _by_id(_render(_sub(tmp_path, "stamped"), source=source, stamp="end-top", stamp_size=2.0))
    column = 2.0 * TEXT + 0.5 * TEXT
    bar, box = stamped["annotation-kind-bar:view-n1"], stamped["annotation-box:view-n1"]
    assert bar.bounds[2] == pytest.approx(box.bounds[2] - column)
    # The declared text-width bound (maxInlineEm 12) still bounds the whole note, column included.
    assert box.bounds[2] <= 12 * TEXT + 1e-6
    assert plain["annotation-box:view-n1"].bounds[2] <= 12 * TEXT + 1e-6
    # A start-side stamp moves the bar and the body past the column.
    start = _by_id(_render(_sub(tmp_path, "start"), source=source, stamp="start-top", stamp_size=2.0))
    box, bar, text = start["annotation-box:view-n1"], start["annotation-kind-bar:view-n1"], start["annotation-text:view-n1"]
    assert bar.bounds[0] == pytest.approx(box.bounds[0] + column)
    assert text.bounds[0] == pytest.approx(box.bounds[0] + column)


def test_a_stamp_taller_than_the_note_sets_the_box_height(tmp_path):
    rendered = _render(tmp_path, source=ak.project(text="Hi"), stamp="end-top", stamp_size=4.0, bar=False,
                       secondary=False, label_fill="text")
    box = _by_id(rendered)["annotation-box:view-n1"]
    stamp = _stamp(rendered, "view-n1")[0]
    assert box.bounds[3] == pytest.approx(4.0 * TEXT) == pytest.approx(stamp.bounds[3])


def test_the_stamp_sits_inside_the_accent_edge(tmp_path):
    rendered = _render(tmp_path, bar=False, accent="end", accent_size=6, label_fill="text", stamp="end-bottom")
    box = _by_id(rendered)["annotation-box:view-n0"]
    x, y, w, h = box.bounds
    stamp = _stamp(rendered, "view-n0")[0]
    assert stamp.bounds[0] + stamp.bounds[2] == pytest.approx(x + w - 6)
    assert stamp.bounds[1] + stamp.bounds[3] == pytest.approx(y + h)


def test_a_bottom_stamp_stands_above_an_accent_edge_on_the_bottom(tmp_path):
    rendered = _render(tmp_path, bar=False, accent="bottom", accent_size=6, label_fill="text", stamp="end-bottom")
    box = _by_id(rendered)["annotation-box:view-n0"]
    stamp = _stamp(rendered, "view-n0")[0]
    assert stamp.bounds[1] + stamp.bounds[3] == pytest.approx(box.bounds[1] + box.bounds[3] - 6)


def test_a_top_stamp_stands_below_an_accent_edge_on_the_top(tmp_path):
    rendered = _render(tmp_path, bar=False, accent="top", accent_size=6, label_fill="text", stamp="start-top")
    box = _by_id(rendered)["annotation-box:view-n0"]
    assert _stamp(rendered, "view-n0")[0].bounds[1] == pytest.approx(box.bounds[1] + 6)


def test_a_balloon_box_may_carry_a_stamp(tmp_path):
    def text_only(parts):
        sr.with_balloon_notes(parts)
        theme = parts["theme"]["body"]
        del theme["roles"]["annotation-kind-bar"]
        del theme["colorBindings"]["annotation-kind-bar.fill"]

    rendered = _render(tmp_path, stamp="end-top", label_fill="text", mutate=text_only)
    assert len(_stamp(rendered, "view-n0")) == SEAL_PARTS["view-n0"]


def test_an_unknown_stamp_glyph_is_an_asset_reference_error_at_the_kind_pointer(tmp_path):
    with pytest.raises(Exception) as failure:
        _render(tmp_path, stamp="end-top", stamps={"risk": "chrona-target-parts:nope"})
    assert "E_THEME_ASSET_REFERENCE" in str(failure.value)


def test_a_stamp_glyph_from_an_unpinned_catalogue_set_is_an_asset_reference_error(tmp_path):
    with pytest.raises(Exception) as failure:
        _render(tmp_path, stamp="end-top", stamps={"risk": "elsewhere:seal"})
    assert "E_THEME_ASSET_REFERENCE" in str(failure.value)


@pytest.mark.parametrize("placement", [{"corner": "middle", "size": 2}, {"corner": "end-top", "size": 0},
                                       {"corner": "end-top", "size": -1}])
def test_an_invalid_stamp_placement_is_rejected_by_the_theme_schema(tmp_path, placement):
    def invalid(parts):
        parts["theme"]["body"]["values"]["kind-stamp-placement"]["value"] = placement

    with pytest.raises(Exception) as failure:
        _render(tmp_path, stamp="end-top", mutate=invalid)
    assert "E_THEME_SCHEMA" in str(failure.value)


def test_the_baseline_profile_rejects_the_stroked_glyph_like_any_catalogue_glyph(tmp_path):
    source = ak.project()
    parts = sr.bundle()
    ak.with_view_notes(parts, source)
    ak.with_kind_theme(parts, stamp="end-top")
    with pytest.raises(Exception) as failure:
        ak.render(tmp_path, source, parts, visual_profile="chrona-output/visual/v0.5-baseline")
    assert "E_VISUAL_CAPABILITY_UNSUPPORTED" in str(failure.value)


def test_rendering_twice_gives_the_same_bytes(tmp_path):
    first = _render(_sub(tmp_path, "a"), stamp="end-top")
    second = _render(_sub(tmp_path, "b"), stamp="end-top")
    assert first.artifact.content == second.artifact.content


def _stamp_findings(document, note, decoration_severity="warning"):
    return [item for item in evaluate_scene_contrast(document, decoration_severity=decoration_severity)
            if item.visual_role == "annotation-kind-stamp" and item.primitive_id.startswith(f"annotation-kind-stamp:{note}")]


def test_the_scene_gate_judges_every_stamp_part_against_the_ground_it_lies_on(tmp_path):
    document = scene_document(_render(tmp_path, stamp="end-top").scene)
    findings = _stamp_findings(document, "view-n0")
    assert len(findings) >= SEAL_PARTS["view-n0"]
    assert all(item.code == "E_SCENE_DECORATION_CONTRAST" and item.severity == "info" for item in findings)


def test_the_parts_of_one_stamp_are_never_each_others_ground(tmp_path):
    # The hazard tab mixes a stroked outline with fill parts of the same ink: judged against the note, not itself.
    rendered = _render(tmp_path, stamp="end-top", stamps={"risk": "chrona-target-parts:hazard-tab"}, bar=False,
                       label_fill="text")
    findings = _stamp_findings(scene_document(rendered.scene), "view-n0")
    assert len(findings) >= 8 and all(item.severity == "info" for item in findings)
    assert {item.ground_id for item in findings} == {"annotation-box:view-n0"}


def test_a_stamp_that_vanishes_into_its_ground_is_a_decoration_error(tmp_path):
    rendered = _render(tmp_path, stamp="end-top", bar=False, label_fill="text")
    document = scene_document(rendered.scene)
    box_fill = _by_id(rendered)["annotation-box:view-n0"].paint.fill
    for primitive in document["surfaces"][0]["primitives"]:
        if primitive["id"].startswith("annotation-kind-stamp:view-n0"):
            primitive["paint"]["stroke"] = box_fill
    # The gate's blocking mode (a Theme's `contrastPolicy`, #995); by default the same miss is a warning.
    errors = [item for item in _stamp_findings(document, "view-n0", "error") if item.severity == "error"]
    assert len(errors) == SEAL_PARTS["view-n0"]
    assert not [item for item in _stamp_findings(document, "view-n1", "error") if item.severity == "error"]
    warned = [item for item in _stamp_findings(document, "view-n0") if item.severity == "warning"]
    assert len(warned) == SEAL_PARTS["view-n0"]
