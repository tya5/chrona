"""`annotationContainer.border`: a per-side CSS-style box border on annotation containers (#1049).

Synthetic notes through the packaged `executive-light` bundle with a 300 px note rail; no `examples/` input. The rules
checked on the published Scene: every bordered side lies on the box's outer edge at its full length with mitred
corners, a width-0 side draws nothing, the content inset is measured from inside the border (text, wrap, `fill`),
nothing stands between a border and the box edge, a border composes with tilt, artwork and leaders, and `balloon`,
`image` are refused, not ignored (a rounded rectangle follows its radius, #1087).
"""
from __future__ import annotations

from pathlib import Path

import pytest

from tests.support import annotation_artwork as aw
from tests.support import annotation_border as ab
from tests.support import annotation_kinds as ak
from tests.support import synthetic_review as sr

W = 4.0
ONE = {side: {"width": W + index} for index, side in enumerate(ab.SIDES)}
TOL = 0.01


def _render(tmp_path, border, **kwargs):
    return ab.render_notes(tmp_path, border, **kwargs)


def _close(left, right):
    return left == pytest.approx(right, abs=TOL)


@pytest.mark.parametrize("side", ab.SIDES)
def test_a_single_side_lies_on_the_box_edge_at_full_length(tmp_path, side):
    rendered = _render(tmp_path, {side: {"width": 5}}, inset=ab.INSET)
    for note, box in ab.boxes(rendered).items():
        strips = ab.strips(rendered, note)
        assert set(strips) == {side}  # nothing for a side that is not declared
        x, y, w, h = box.bounds
        sx, sy, sw, sh = strips[side].bounds
        expected = {"start": (x, y, 5, h), "end": (x + w - 5, y, 5, h), "top": (x, y, w, 5), "bottom": (x, y + h - 5, w, 5)}[side]
        assert all(_close(got, want) for got, want in zip((sx, sy, sw, sh), expected))
        assert strips[side].kind.value == "Rect"  # an unmitred strip is a plain rectangle


def test_two_sides_meet_in_a_mitre_and_each_spans_its_full_side(tmp_path):
    rendered = _render(tmp_path, {"start": {"width": 3}, "top": {"width": 2}}, inset=ab.INSET)
    for note, box in ab.boxes(rendered).items():
        x, y, w, h = box.bounds
        strips = ab.strips(rendered, note)
        assert set(strips) == {"start", "top"}
        start, top = ab.points(strips["start"]), ab.points(strips["top"])
        # CSS mitre: from the outer corner to the padding corner, shared by both strips.
        assert _close(start[0][0], x) and _close(start[0][1], y) and _close(start[1][0], x + 3) and _close(start[1][1], y + 2)
        assert _close(top[0][0], x) and _close(top[1][0], x + w) and _close(top[3][0], x + 3) and _close(top[3][1], y + 2)
        assert (round(start[1][0], 6), round(start[1][1], 6)) == (round(top[3][0], 6), round(top[3][1], 6))
        assert strips["start"].kind.value == "Symbol" and strips["top"].kind.value == "Symbol"
        # outer edges on the box edge, full length (bounds of the strip)
        assert _close(strips["start"].bounds[3], h) and _close(strips["top"].bounds[2], w)
        assert _close(strips["start"].bounds[0], x) and _close(strips["top"].bounds[1], y)


def test_a_width_zero_side_emits_no_primitive_and_no_space(tmp_path):
    with_zero = _render(tmp_path, {"start": {"width": 3}, "end": {"width": 0}, "top": {"width": 0}}, name="a")
    plain = _render(tmp_path, {"start": {"width": 3}}, name="b")
    assert set(ab.strips(with_zero)) == {"start"}
    assert {k: v.bounds for k, v in ab.boxes(with_zero).items()} == {k: v.bounds for k, v in ab.boxes(plain).items()}


def test_the_inset_is_measured_from_inside_the_border(tmp_path):
    rendered = _render(tmp_path, ONE, inset=ab.INSET, words=6, name="b")
    plain = _render(tmp_path, None, inset=ab.INSET, words=6, name="p")
    for note, box in ab.boxes(rendered).items():
        text = ab.prims(rendered, "annotation-text")[note]
        size = text.text_layout.font_size
        x, y, w, h = box.bounds
        # inset from each bordered side by at least the border width plus the content inset
        assert text.bounds[0] >= x + ONE["start"]["width"] + ab.INSET["left"] * size - TOL
        assert text.bounds[0] + text.bounds[2] <= x + w - ONE["end"]["width"] - ab.INSET["right"] * size + TOL
        assert text.bounds[1] >= y + ONE["top"]["width"] + ab.INSET["top"] * size - TOL
        assert text.bounds[1] + text.bounds[3] <= y + h - ONE["bottom"]["width"] - ab.INSET["bottom"] * size + TOL
        # outer size = content + inset + border
        base = ab.boxes(plain)[note].bounds
        assert _close(w, base[2] + ONE["start"]["width"] + ONE["end"]["width"])
        assert _close(h, base[3] + ONE["top"]["width"] + ONE["bottom"]["width"])


def test_nothing_stands_between_the_border_and_the_box_edge(tmp_path):
    rendered = _render(tmp_path, {"start": {"width": 6, "paint": "kind"}}, inset=ab.INSET, kind_ink=True,
                       configure=lambda parts: ak.with_kind_theme(parts, bar=False, label_fill="text"))
    for note, box in ab.boxes(rendered).items():
        x = box.bounds[0]
        strip = ab.strips(rendered, note)["start"]
        assert _close(strip.bounds[0], x)
        for item in rendered.surface.primitives:
            if item.source_ref == note and item.scene_id.startswith(("annotation-text:", "annotation-kind-text:", "annotation-kind-bar:")):
                assert item.bounds[0] >= x + 6 - TOL


def test_a_theme_without_a_border_is_byte_identical(tmp_path):
    plain = _render(tmp_path, None, name="a", inset=ab.INSET)
    bare = ab.render_notes(tmp_path, None, name="b", inset=ab.INSET, ink_roles=())
    assert bare.artifact.content == plain.artifact.content
    assert not ab.prims(plain, "annotation-border")


def test_the_ink_of_each_side_is_its_own_role_and_the_kind_paint_uses_the_kind_colour(tmp_path):
    rendered = _render(tmp_path, {"start": {"width": 3}, "end": {"width": 3}, "top": {"width": 3}, "bottom": {"width": 3}})
    fills = {side: item.paint.fill.upper() for side, item in ab.strips(rendered).items()}
    assert len(set(fills.values())) == 3  # start and bottom share a colour binding, end and top differ
    assert fills["start"] == fills["bottom"] and fills["end"] != fills["start"] != fills["top"]
    kind = _render(tmp_path, {"start": {"width": 3, "paint": "kind"}, "top": {"width": 2}}, kind_ink=True, name="k",
                   configure=lambda parts: ak.with_kind_theme(parts, bar=False, label_fill="text"))
    strips = ab.strips(kind)
    assert strips["start"].paint.fill.upper() == ak.KIND_COLORS["kind-report"]
    assert strips["top"].paint.fill.upper() == fills["top"]  # an ink side is never recoloured by the kind


def test_a_declared_side_with_no_ink_role_is_a_theme_error(tmp_path):
    with pytest.raises(Exception) as caught:
        _render(tmp_path, {"start": {"width": 3}}, ink_roles=())
    assert "E_THEME_ROLE_REQUIRED" in str(caught.value)
    with pytest.raises(Exception) as caught:
        _render(tmp_path, {"start": {"width": 3, "paint": "kind"}}, name="k")
    assert "E_THEME_ROLE_REQUIRED" in str(caught.value)


@pytest.mark.parametrize("kwargs,code", [
    ({"outline": "balloon", "radius": 0.2}, "E_THEME_SCHEMA"),
    ({"border": {}}, "E_THEME_SCHEMA"),
])
def test_balloon_and_an_empty_border_are_refused_by_the_schema_not_ignored(tmp_path, kwargs, code):
    border = kwargs.pop("border", {"start": {"width": 3}})
    with pytest.raises(Exception) as caught:
        _render(tmp_path, border, **kwargs)
    assert code in str(caught.value) or code in repr(caught.value)


@pytest.mark.parametrize("border", [
    {"middle": {"width": 3}}, {"start": {}}, {"start": {"width": -1}}, {"start": {"width": "3"}},
    {"start": {"width": 3, "paint": "red"}}, {"start": {"width": 3, "style": "dashed"}}, {"start": 3},
])
def test_a_malformed_border_is_rejected(tmp_path, border):
    with pytest.raises(Exception) as caught:
        _render(tmp_path, border)
    assert "E_THEME_SCHEMA" in str(caught.value) or "E_THEME_SCHEMA" in repr(caught.value)


def test_a_filled_note_wraps_inside_the_border_and_keeps_the_slot_extent(tmp_path):
    rendered = _render(tmp_path, ONE, inset=ab.INSET, extra={"inlineSize": "fill"}, words=8)
    for note, box in ab.boxes(rendered).items():
        text = ab.prims(rendered, "annotation-text")[note]
        size = text.text_layout.font_size
        assert _close(box.bounds[2], ab.RAIL)
        inner = ab.RAIL - ONE["start"]["width"] - ONE["end"]["width"] - (ab.INSET["left"] + ab.INSET["right"]) * size
        assert text.bounds[2] <= inner + TOL
        assert len(text.text_layout.lines) >= 2
        assert {"start", "end", "top", "bottom"} == set(ab.strips(rendered, note))
        assert _close(ab.strips(rendered, note)["end"].bounds[0] + ONE["end"]["width"], box.bounds[0] + box.bounds[2])


@pytest.mark.parametrize("angle", [-3.0, 4.0])
def test_a_tilted_note_rotates_its_border_with_the_frame(tmp_path, angle):
    rendered = _render(tmp_path, {"start": {"width": 5}, "top": {"width": 3}}, inset=ab.INSET,
                       extra={"tiltDegrees": [angle], "inlineSize": "fill"}, words=5)
    for note, box in ab.boxes(rendered).items():
        corners = ab.points(box)
        strips = ab.strips(rendered, note)
        start, top = ab.points(strips["start"]), ab.points(strips["top"])
        # the strips' outer edge is the rotated frame's own edge: the start strip stands on corner 0 -> corner 3
        assert all(a == pytest.approx(b, abs=TOL) for a, b in zip(start[0], corners[0]))
        assert all(a == pytest.approx(b, abs=TOL) for a, b in zip(start[3], corners[3]))
        assert all(a == pytest.approx(b, abs=TOL) for a, b in zip(top[1], corners[1]))
        assert strips["start"].kind.value == "Symbol"
        assert _close(box.bounds[2], ab.RAIL)  # fill still equals the slot with the border in the chrome


def test_the_paint_order_is_box_artwork_border_kind_frame_text(tmp_path):
    def configure(parts):
        aw.with_artwork(parts, content=aw.CONTENT_INSET, extra={"border": {"start": {"width": 4, "paint": "kind"}}})
        ak.with_kind_theme(parts, bar=True)
        parts["theme"]["body"]["roles"]["annotation-kind-accent"] = {}
        parts["theme"]["body"]["colorBindings"]["annotation-kind-accent.fill"] = "accent"
    directory = tmp_path / "a"
    directory.mkdir()
    parts = sr.bundle()
    sr.with_note_rail(parts, ab.RAIL)
    configure(parts)
    source = sr.chain_project()
    sr.add_notes(source, parts["view"], ab.TARGETS[:1], [ab.rail_candidate()])
    rendered = ak.render(directory, source, parts)
    order = [item.scene_id.split(":")[0] for item in sorted(
        (item for item in rendered.surface.primitives if item.source_ref == "note-0"
         and item.scene_id.split(":")[0] in {"annotation-box", "annotation-artwork", "annotation-border",
                                              "annotation-kind-bar", "annotation-kind-text", "annotation-text"}),
        key=lambda item: item.paint_order)]
    first = {name: order.index(name) for name in dict.fromkeys(order)}
    assert first["annotation-box"] < first["annotation-artwork"] < first["annotation-border"]
    assert first["annotation-border"] < first["annotation-kind-bar"] < first["annotation-text"]


def test_a_leader_still_ends_on_the_outer_edge_of_the_bordered_box(tmp_path):
    rendered = _render(tmp_path, {"start": {"width": 8}}, inset=ab.INSET)
    plain = _render(tmp_path, None, inset=ab.INSET, name="p")
    for note, box in ab.boxes(rendered).items():
        leader = ab.prims(rendered, "annotation-leader").get(note) or next(
            item for item in rendered.surface.primitives if item.source_ref == note and "leader" in item.scene_id)
        x, y, w, h = box.bounds
        ends = [command.points[0] for command in leader.path_commands] if leader.path_commands else list(leader.points)
        assert any(abs(px - x) < 0.5 or abs(px - (x + w)) < 0.5 or abs(py - y) < 0.5 or abs(py - (y + h)) < 0.5
                   for px, py in ends)
        assert ab.boxes(plain)[note].bounds[0] == pytest.approx(x, abs=TOL)  # the start edge does not move


def test_the_legacy_edge_accent_is_unchanged_and_still_inside_the_inset(tmp_path):
    def configure(parts):
        ak.with_kind_theme(parts, bar=False, accent="start", accent_size=6, label_fill="text")
    rendered = ab.render_notes(tmp_path, None, inset=ab.INSET, configure=configure, ink_roles=())
    for note, box in ab.boxes(rendered).items():
        accent = ab.prims(rendered, "annotation-kind-accent")[note]
        size = ab.prims(rendered, "annotation-text")[note].text_layout.font_size
        assert accent.bounds[0] == pytest.approx(box.bounds[0] + ab.INSET["left"] * size, abs=TOL)  # today's look
        assert not ab.prims(rendered, "annotation-border")


@pytest.mark.parametrize("side", ["leading", "trailing"])
def test_a_label_visual_stands_inside_the_border(tmp_path, side):
    material = next(parent for parent in Path(__file__).resolve().parents if (parent / "pyproject.toml").is_file()
                    ) / "src/chrona/resources/icons/material-symbols-outline-rounded-v2026-09-22.yaml"
    source = ak.project(("note",), text="i " * 60)
    parts = sr.bundle()
    ak.with_view_notes(parts, source)
    sr.with_note_rail(parts, ab.RAIL)
    ab.with_border(parts, {"start": {"width": 7}, "end": {"width": 9}}, extra={"inlineSize": "fill"})
    parts["view"]["body"]["visuals"] = [{"target": {"kind": "annotation", "id": "view-n0"},
                                         "ref": "material:10k-outline-rounded", "decorative": True, "side": side}]
    for annotation in parts["view"]["body"]["annotations"]:
        annotation["candidates"] = [ab.rail_candidate()]
    directory = tmp_path / side
    directory.mkdir()
    rendered = ak.render(directory, source, parts, catalogs=(material,), visual_profile="chrona-output/visual/v0.7-svg")
    box = next(iter(ab.boxes(rendered).values()))
    icon = next(item for item in rendered.surface.primitives if item.scene_id.startswith("visual:annotation-text:"))
    x, _, w, _ = box.bounds
    assert icon.bounds[0] >= x + 7 - TOL and icon.bounds[0] + icon.bounds[2] <= x + w - 9 + TOL
