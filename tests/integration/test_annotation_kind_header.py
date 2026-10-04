"""#584 A584-1: the annotation kind header (title bar, header text, accent edge), rendered end to end.

A Project with Project annotations of two kinds goes through the packaged `executive-light` bundle with a
Theme that dresses them (`tests/support/annotation_kinds.py`). No `examples/` input.
"""
from __future__ import annotations

from copy import deepcopy

import pytest

from chrona.presentation.scene.contrast_policy import evaluate_scene_contrast
from chrona.presentation.scene.serialization import scene_document
from tests.support import annotation_kinds as ak
from tests.support import synthetic_review as sr

LABEL, SECONDARY = 16 * 1.2, 11 * 1.2  # the two header line heights of the fixture Theme
PAD_INLINE = 0.6 * 16
PAD_BLOCK = PAD_INLINE / 2


def _parts(source, *, theme=None, mutate=None):
    parts = sr.bundle()
    ak.with_view_notes(parts, source)
    if theme is not None:
        ak.with_kind_theme(parts, **theme)
    if mutate is not None:
        mutate(parts)
    return parts


def _render(tmp_path, source=None, **options):
    source = source or ak.project()
    return sr.render(tmp_path, source, presentation=_parts(source, **options))


def _by_id(rendered):
    return {item.scene_id: item for item in rendered.surface.primitives}


def _sub(tmp_path, name):
    path = tmp_path / name
    path.mkdir()
    return path


def _bounds(item):
    return tuple(round(value, 6) for value in item.bounds)


def test_without_a_kind_declaration_the_note_is_unchanged(tmp_path):
    source = ak.project()
    plain = _render(_sub(tmp_path, "plain"), source)
    # A Theme that dresses no kind of this Project, and an unrelated declaration, change nothing.
    other = _render(_sub(tmp_path, "other"), source, theme={"kinds": {"unrelated": ak.KINDS["risk"]}})
    assert list(other.surface.primitives) == list(plain.surface.primitives)
    assert other.artifact.content == plain.artifact.content
    ids = _by_id(plain)
    assert not any(key.startswith("annotation-kind-") for key in ids)


def test_a_kind_declared_in_the_theme_but_absent_from_the_project_dresses_nothing(tmp_path):
    source = ak.project(kinds=("other", "other"))
    plain = _render(_sub(tmp_path, "plain"), source)
    dressed = _render(_sub(tmp_path, "dressed"), source, theme={})
    assert list(dressed.surface.primitives) == list(plain.surface.primitives)


def test_an_annotation_carrying_its_own_text_has_no_kind(tmp_path):
    source = ak.project()

    def own_text(parts):
        for entry in parts["view"]["body"]["annotations"]:
            entry["text"] = source["annotations"][entry.pop("projectAnnotation")]["text"]

    plain = _render(_sub(tmp_path, "plain"), source, mutate=own_text)
    dressed = _render(_sub(tmp_path, "dressed"), source, theme={}, mutate=own_text)
    assert list(dressed.surface.primitives) == list(plain.surface.primitives)


def test_the_header_text_is_the_label_the_subject_and_the_secondary_line_of_each_kind(tmp_path):
    ids = _by_id(_render(tmp_path, theme={}))
    assert ids["annotation-kind-text:view-n0:0"].text == "RISK · Task 0"
    assert ids["annotation-kind-text:view-n0:1"].text == "WARNING"
    assert ids["annotation-kind-text:view-n1:0"].text == "NOTE"
    assert ids["annotation-kind-text:view-n1:1"].text == "REPORT"
    assert ids["annotation-kind-text:view-n0:0"].visual_role == "annotation-kind-label"
    assert ids["annotation-kind-text:view-n0:1"].visual_role == "annotation-kind-secondary"


def test_without_a_secondary_role_the_second_line_is_absent(tmp_path):
    ids = _by_id(_render(tmp_path, theme={"secondary": False}))
    assert "annotation-kind-text:view-n0:0" in ids and "annotation-kind-text:view-n0:1" not in ids


def test_without_a_label_role_there_is_no_header_and_so_no_bar(tmp_path):
    def drop_label(parts):
        theme = parts["theme"]["body"]
        for role in ("annotation-kind-label", "annotation-kind-secondary"):
            del theme["roles"][role]
            del theme["colorBindings"][f"{role}.fill"]

    ids = _by_id(_render(tmp_path, theme={}, mutate=drop_label))
    assert not any(key.startswith(("annotation-kind-text", "annotation-kind-bar")) for key in ids)


def test_each_kind_paints_its_bar_with_its_own_scheme_colour(tmp_path):
    ids = _by_id(_render(tmp_path, theme={}))
    assert ids["annotation-kind-bar:view-n0"].paint.fill == ak.KIND_COLORS["kind-alert"]
    assert ids["annotation-kind-bar:view-n1"].paint.fill == ak.KIND_COLORS["kind-report"]


def test_a_kind_without_a_colour_keeps_the_bar_role_fill(tmp_path):
    kinds = deepcopy(ak.KINDS)
    del kinds["risk"]["color"]
    ids = _by_id(_render(tmp_path, theme={"kinds": kinds}))
    assert ids["annotation-kind-bar:view-n0"].paint.fill == ak.KIND_COLORS["kind-alert"]  # the role binding
    assert ids["annotation-kind-bar:view-n1"].paint.fill == ak.KIND_COLORS["kind-report"]  # the kind colour


def test_the_bar_covers_the_header_block_across_the_box_width(tmp_path):
    ids = _by_id(_render(tmp_path, theme={}))
    for note in ("view-n0", "view-n1"):
        box, bar = ids[f"annotation-box:{note}"], ids[f"annotation-kind-bar:{note}"]
        assert bar.bounds[0] == pytest.approx(box.bounds[0]) and bar.bounds[1] == pytest.approx(box.bounds[1])
        assert bar.bounds[2] == pytest.approx(box.bounds[2])
        assert bar.bounds[3] == pytest.approx(LABEL + SECONDARY + 2 * PAD_BLOCK)


def test_the_header_text_sits_inside_the_bar_padding(tmp_path):
    ids = _by_id(_render(tmp_path, theme={}))
    bar = ids["annotation-kind-bar:view-n0"]
    first, second = ids["annotation-kind-text:view-n0:0"], ids["annotation-kind-text:view-n0:1"]
    assert first.baseline[0] == pytest.approx(bar.bounds[0] + PAD_INLINE)
    assert first.baseline[1] == pytest.approx(bar.bounds[1] + PAD_BLOCK + 16)
    assert second.baseline[1] == pytest.approx(bar.bounds[1] + PAD_BLOCK + LABEL + 11)


def test_the_box_grows_by_the_header_block_and_the_body_text_moves_below_it(tmp_path):
    source = ak.project()
    plain = _by_id(_render(_sub(tmp_path, "plain"), source))
    dressed = _by_id(_render(_sub(tmp_path, "dressed"), source, theme={}))
    block = LABEL + SECONDARY + 2 * PAD_BLOCK
    for note in ("view-n0", "view-n1"):
        before, after = plain[f"annotation-box:{note}"], dressed[f"annotation-box:{note}"]
        assert after.bounds[3] == pytest.approx(before.bounds[3] + block)
        body = dressed[f"annotation-text:{note}"]
        assert body.bounds[1] == pytest.approx(after.bounds[1] + block)
        assert body.bounds[0] == pytest.approx(after.bounds[0])


def test_a_long_header_widens_the_box_to_its_own_width(tmp_path):
    kinds = deepcopy(ak.KINDS)
    kinds["note"]["label"] = "A VERY LONG KIND LABEL FOR A SHORT NOTE"
    ids = _by_id(_render(tmp_path, theme={"kinds": kinds}))
    box, label, body = ids["annotation-box:view-n1"], ids["annotation-kind-text:view-n1:0"], ids["annotation-text:view-n1"]
    assert label.bounds[2] + 2 * PAD_INLINE > body.bounds[2]
    assert box.bounds[2] == pytest.approx(label.bounds[2] + 2 * PAD_INLINE)


def test_the_bar_is_emitted_after_the_box_and_before_the_header_text_in_paint_order(tmp_path):
    rendered = _render(tmp_path, theme={})
    order = [item.scene_id for item in rendered.surface.primitives]
    box, bar = order.index("annotation-box:view-n0"), order.index("annotation-kind-bar:view-n0")
    text = order.index("annotation-kind-text:view-n0:0")
    assert box < bar < text
    ids = _by_id(rendered)
    assert ids["annotation-box:view-n0"].paint_order == ids["annotation-kind-bar:view-n0"].paint_order == 400
    assert ids["annotation-kind-text:view-n0:0"].paint_order == 401


@pytest.mark.parametrize("side", ["start", "end", "top", "bottom"])
def test_the_kind_border_stands_on_its_side_and_grows_the_box_by_its_width(tmp_path, side):
    source = ak.project()
    plain = _by_id(_render(_sub(tmp_path, "plain"), source))["annotation-box:view-n0"]
    ids = _by_id(_render(_sub(tmp_path, "accent"), source, theme={"bar": False, "border_side": side, "border_width": 6,
                                                                   "label_fill": "text"}))
    box, accent = ids["annotation-box:view-n0"], ids[f"annotation-border:view-n0:{side}"]
    assert not any(key.startswith("annotation-kind-accent:") for key in ids)
    x, y, w, h = box.bounds
    expected = {"start": (x, y, 6, h), "end": (x + w - 6, y, 6, h), "top": (x, y, w, 6), "bottom": (x, y + h - 6, w, 6)}[side]
    assert accent.bounds == pytest.approx(expected)
    header = LABEL + SECONDARY  # no bar: the lines stack with no padding
    if side in {"start", "end"}:
        assert w == pytest.approx(plain.bounds[2] + 6)
        assert h == pytest.approx(plain.bounds[3] + header)
    else:
        assert h == pytest.approx(plain.bounds[3] + header + 6)
    text = ids["annotation-text:view-n0"]
    assert text.bounds[0] == pytest.approx(x + (6 if side == "start" else 0))
    assert text.bounds[1] == pytest.approx(y + (6 if side == "top" else 0) + header)
    assert accent.paint.fill == ak.KIND_COLORS["kind-alert"]


def test_the_bar_leaves_the_kind_border_its_own_edge(tmp_path):
    ids = _by_id(_render(tmp_path, theme={"border_side": "start", "border_width": 6}))
    box, bar = ids["annotation-box:view-n0"], ids["annotation-kind-bar:view-n0"]
    assert bar.bounds[0] == pytest.approx(box.bounds[0] + 6)
    assert bar.bounds[2] == pytest.approx(box.bounds[2] - 6)


def test_a_bar_on_a_balloon_box_is_a_declaration_conflict(tmp_path):
    source = ak.project()
    with pytest.raises(Exception) as failure:
        _render(tmp_path, source, theme={}, mutate=sr.with_balloon_notes)
    assert "E_LAYOUT_ANNOTATION_KIND_FRAME_OUTLINE" in str(failure.value)


def test_a_balloon_box_may_carry_header_text_alone(tmp_path):
    def text_only(parts):
        sr.with_balloon_notes(parts)
        theme = parts["theme"]["body"]
        del theme["roles"]["annotation-kind-bar"]
        del theme["colorBindings"]["annotation-kind-bar.fill"]

    ids = _by_id(_render(tmp_path, theme={"label_fill": "text"}, mutate=text_only))
    assert ids["annotation-kind-text:view-n0:0"].text == "RISK · Task 0"


def test_rendering_twice_gives_the_same_bytes(tmp_path):
    first = _render(_sub(tmp_path, "a"), theme={"border_side": "end"})
    second = _render(_sub(tmp_path, "b"), theme={"border_side": "end"})
    assert first.artifact.content == second.artifact.content


def _document(rendered):
    return scene_document(rendered.scene)


def _findings(document, role, decoration_severity="warning"):
    return [item for item in evaluate_scene_contrast(document, decoration_severity=decoration_severity)
            if item.visual_role == role]


def test_the_scene_gate_judges_each_header_text_on_its_own_kind_bar(tmp_path):
    rendered = _render(tmp_path, theme={"border_side": "start"})
    document = _document(rendered)
    labels = _findings(document, "annotation-kind-label")
    assert {item.primitive_id for item in labels} == {"annotation-kind-text:view-n0:0", "annotation-kind-text:view-n1:0"}
    by_text = {item.primitive_id: item for item in labels}
    assert by_text["annotation-kind-text:view-n0:0"].ground_id == "annotation-kind-bar:view-n0"
    assert by_text["annotation-kind-text:view-n1:0"].ground_id == "annotation-kind-bar:view-n1"
    assert all(item.severity == "info" and item.floor == 4.5 for item in labels)
    secondary = _findings(document, "annotation-kind-secondary")
    assert {item.ground_id for item in secondary} == {"annotation-kind-bar:view-n0", "annotation-kind-bar:view-n1"}
    for role in ("annotation-kind-bar", "annotation-kind-accent"):
        decoration = _findings(document, role)
        assert len(decoration) == 2 and all(item.severity == "info" for item in decoration)


def _paint(document, primitive_id, color):
    for primitive in document["surfaces"][0]["primitives"]:
        if primitive["id"] == primitive_id:
            primitive["paint"]["fill"] = color
            return
    raise KeyError(primitive_id)


def test_a_bar_too_close_to_the_label_is_a_gate_error_on_that_annotation_only(tmp_path):
    document = _document(_render(tmp_path, theme={}))
    _paint(document, "annotation-kind-bar:view-n0", "#F2F2F2")
    failing = {item.primitive_id for item in _findings(document, "annotation-kind-label") if item.severity == "error"}
    assert failing == {"annotation-kind-text:view-n0:0"}
    assert {item.primitive_id for item in _findings(document, "annotation-kind-secondary")
            if item.severity == "error"} == {"annotation-kind-text:view-n0:1"}


def test_an_accent_that_vanishes_into_the_note_box_is_a_decoration_error(tmp_path):
    rendered = _render(tmp_path, theme={"bar": False, "border_side": "start", "label_fill": "text"})
    document = _document(rendered)
    box_fill = _by_id(rendered)["annotation-box:view-n0"].paint.fill
    _paint(document, "annotation-border:view-n0:start", box_fill)
    errors = [item for item in _findings(document, "annotation-kind-accent", "error") if item.severity == "error"]
    assert [item.primitive_id for item in errors] == ["annotation-border:view-n0:start"]
    assert errors[0].code == "E_SCENE_DECORATION_CONTRAST"
    # Without the Theme's blocking declaration (#995) the same miss is a warning.
    (warned,) = [item for item in _findings(document, "annotation-kind-accent") if item.severity == "warning"]
    assert warned.code == "W_SCENE_DECORATION_CONTRAST"


def test_header_text_without_a_bar_is_judged_on_the_note_box(tmp_path):
    rendered = _render(tmp_path, theme={"bar": False, "label_fill": "text"})
    box = _by_id(rendered)["annotation-box:view-n0"]
    labels = _findings(_document(rendered), "annotation-kind-label")
    assert {item.ground_id for item in labels} == {"annotation-box:view-n0", "annotation-box:view-n1"}
    assert all(item.ground_color == box.paint.fill for item in labels if item.ground_id == "annotation-box:view-n0")
