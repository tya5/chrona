"""The Theme `group-tab` role (#882): a patterned tab on each group header, end to end.

A synthetic Project grouped by owner goes through the packaged `control-room-dark` bundle with the packaged
`chrona-target-parts` catalogue, so no corpus edit can change what these tests prove. The committed Title
Card-style slide is evidence, not a gate. No test reads `examples/`.
"""
from __future__ import annotations

import io
from copy import deepcopy
from datetime import date, timedelta
from pathlib import Path

import pytest
import resvg_py
from PIL import Image

from chrona.presentation.renderers.v05_typeset import render_v05_tikz, render_v05_typst
from chrona.presentation.scene.contrast_policy import evaluate_scene_contrast
from chrona.presentation.scene.serialization import scene_document
from chrona.resources import schema_validator
from chrona.usecases.render_review import RenderFailed
from tests.support import synthetic_review as sr

ROOT = Path(__file__).resolve().parents[2]
CATALOGUE = ROOT / "src/chrona/resources/icons/chrona-target-parts-v2026-10-09.yaml"
STRIPES = "chrona-target-parts:hazard-stripes"
OWNERS = ("bus", "payload", "ground")
YELLOW, DARK = "#FFC857", "#0B1220"  # the packaged `warning` and `surface` colours


def _source(title: str | None = None) -> dict:
    objects = {}
    for index, owner in enumerate(OWNERS):
        for number in range(2):
            key = f"t-{owner}-{number}"
            objects[key] = sr.span(key, date(2026, 1, 5) + timedelta(days=index * 20 + number * 15), 12, owner=owner)
    source = sr.project(objects)
    for owner in OWNERS:
        source["entities"][owner]["title"] = title or owner.title()
    return source


def _parts(*, inline: float | None = 40, block: float | None = None, gap: float | None = 6, position: str | None = None,
           pattern: bool = True, opacity: float = 1, treatment: str = "fill", fill: str = "warning",
           stroke: str = "surface", band_opacity: float | None = None, order: int = 20, declare: bool = True) -> dict:
    """The bundle, with a `group-tab` role when `declare` (Theme v0.13 admits a catalogue pattern on it)."""
    parts = sr.bundle("control-room-dark")
    parts["theme"]["version"] = "chrona/theme/v0.15"
    body = parts["theme"]["body"]
    if band_opacity is not None:  # the group band alone, so no two row stripes overlap each other
        body["values"]["opacity.band"] = {"type": "number", "value": band_opacity}
        body["roles"]["group-band"]["opacity"] = "opacity.band"
    if not declare:
        return parts
    role: dict = {"backgroundTreatment": treatment, "backgroundPaintOrder": order, "opacity": "tab.opacity"}
    body["values"]["tab.opacity"] = {"type": "number", "value": opacity}
    for name, value in (("tabInlineSize", inline), ("tabBlockSize", block), ("tabGap", gap)):
        if value is not None:
            body["values"][f"tab.{name}"] = {"type": "number", "value": value}
            role[name] = f"tab.{name}"
    if position is not None:
        role["tabPosition"] = position
    if pattern:
        body["values"]["tab.pattern"] = {"type": "pattern", "value": {"kind": "catalog", "ref": STRIPES}}
        role["pattern"] = "tab.pattern"
    bindings = {"group-tab.fill": fill}
    if pattern:
        bindings["group-tab.stroke"] = stroke  # the pattern's ink
    if treatment == "outline":
        body["values"]["tab.width"] = {"type": "number", "value": 2}
        role["strokeWidth"] = "tab.width"
        bindings = {"group-tab.stroke": stroke}
    body["roles"]["group-tab"] = role
    body["colorBindings"].update(bindings)
    return parts


def _render(tmp_path, parts, source=None):
    return sr.render(tmp_path, source or _source(), presentation=parts, icon_catalogs=(CATALOGUE,))


def _by_id(rendered) -> dict:
    return {item.scene_id: item for item in rendered.surface.primitives}


def _headers(rendered) -> dict:
    return {group.group_id: group.header_bounds for group in rendered.surface.groups}


def _ellipsized(rendered) -> set[str]:
    return {record.payload["placementId"] for record in rendered.warning_records
            if record.payload["code"] == "W_LAYOUT_TEXT_ELLIPSIZED"}


def _png(rendered, directory) -> Image.Image:
    path = directory / "board.svg"
    path.write_bytes(rendered.artifact.content)
    return Image.open(io.BytesIO(bytes(resvg_py.svg_to_bytes(svg_path=str(path), zoom=1, font_dirs=[],
                                                              skip_system_fonts=False)))).convert("RGB")


def _gate(rendered, primitive_id: str, decoration_severity: str = "warning"):
    return [item for item in evaluate_scene_contrast(scene_document(rendered.scene),
                                                     decoration_severity=decoration_severity)
            if item.primitive_id == primitive_id]


# --- defaults ---------------------------------------------------------------------------------------------


def test_a_theme_without_the_role_draws_no_tab_and_the_same_scene_as_a_role_that_draws_none(tmp_path):
    (tmp_path / "none").mkdir()
    (tmp_path / "empty").mkdir()
    plain = _render(tmp_path, _parts(declare=False))
    none = _render(tmp_path / "none", _parts(treatment="none", inline=None, gap=None, pattern=False))
    parts = _parts(declare=False)
    parts["theme"]["body"]["roles"]["group-tab"] = {}
    empty = _render(tmp_path / "empty", parts)

    def drawing(rendered) -> list:
        """The completed surfaces without the dispositions, which only name an explicit `none` (provenance is apart)."""
        return [{key: value for key, value in surface.items() if key != "decorationDispositions"}
                for surface in scene_document(rendered.scene)["surfaces"]]

    assert not [name for name in _by_id(plain) if name.startswith("group-tab:")]
    assert drawing(plain) == drawing(none) == drawing(empty)
    assert "decorationDispositions" not in scene_document(plain.scene)["surfaces"][0]
    assert {"visualRole": "group-tab", "disposition": "absent"} in scene_document(none.scene)["surfaces"][0][
        "decorationDispositions"]


# --- geometry ---------------------------------------------------------------------------------------------


def test_one_tab_per_header_stands_on_the_inline_start_and_the_header_text_follows_it(tmp_path):
    rendered = _render(tmp_path, _parts())
    found, headers = _by_id(rendered), _headers(rendered)

    assert {name for name in found if name.startswith("group-tab:")} == {f"group-tab:{owner}" for owner in OWNERS}
    for owner in OWNERS:
        tab, text, header = found[f"group-tab:{owner}"], found[f"group-header:{owner}"], headers[owner]
        assert tab.bounds == (header[0], header[1], 40.0, header[3])
        assert text.bounds[0] == pytest.approx(header[0] + 40 + 6)
        assert (tab.source_ref, tab.purpose, tab.visual_role) == (owner, "group-tab", "group-tab")


def test_an_end_tab_stands_on_the_inline_end_and_the_text_keeps_the_start(tmp_path):
    rendered = _render(tmp_path, _parts(position="end"))
    found, headers = _by_id(rendered), _headers(rendered)

    for owner in OWNERS:
        header = headers[owner]
        assert found[f"group-tab:{owner}"].bounds == (header[0] + header[2] - 40, header[1], 40.0, header[3])
        assert found[f"group-header:{owner}"].bounds[0] == pytest.approx(header[0])


@pytest.mark.parametrize("position", ["start", "end"])
def test_the_text_is_bounded_by_the_room_the_tab_and_its_gap_leave_and_the_source_is_kept(tmp_path, position):
    title = "Title " * 6
    plain = _render(tmp_path, _parts(declare=False), _source(title))
    (tmp_path / "tab").mkdir()
    header = _headers(plain)["bus"]
    natural = _by_id(plain)["group-header:bus"].bounds[2]
    room = natural - 20  # less than the title needs
    tabbed = _render(tmp_path / "tab", _parts(inline=header[2] - room - 10, gap=10, position=position), _source(title))

    text = _by_id(tabbed)["group-header:bus"]
    assert _by_id(plain)["group-header:bus"].text == title and "…" not in title
    assert text.text.endswith("…") and text.text.startswith("Title Title")
    assert text.bounds[2] <= room
    if position == "end":
        assert text.bounds[0] + text.bounds[2] <= _by_id(tabbed)["group-tab:bus"].bounds[0] - 10
    else:
        assert text.bounds[0] + text.bounds[2] <= header[0] + header[2]
    assert _ellipsized(tabbed) == {f"group-header:{owner}" for owner in OWNERS}
    assert _ellipsized(plain) == set()


def test_layout_marks_the_shortened_header_text_ellipsized_and_the_others_fit(tmp_path, monkeypatch):
    from chrona.presentation.scene import v05_builder

    placed = []
    real = v05_builder.compose_surface_layout
    def capture(request, *, prepared=None):
        placed.append(real(request, prepared=prepared))
        return placed[-1]

    monkeypatch.setattr(v05_builder, "compose_surface_layout", capture)
    title = "Title " * 6
    header = _headers(_render(tmp_path, _parts(declare=False), _source(title)))["bus"]
    (tmp_path / "tab").mkdir()
    placed.clear()
    _render(tmp_path / "tab", _parts(inline=header[2] - 200, gap=10), _source(title))
    (tmp_path / "fit").mkdir()
    placed_tab = placed[-1]
    _render(tmp_path / "fit", _parts(), _source())

    def dispositions(composition) -> set[tuple[str, str]]:
        return {(item.placement_id, item.overflow) for item in composition.placement.text
                if item.placement_id.startswith("group-header:")}

    assert {overflow for _, overflow in dispositions(placed_tab)} == {"ellipsized"}
    assert {overflow for _, overflow in dispositions(placed[-1])} == {"fit"}


def test_a_header_without_a_tab_keeps_its_text_whatever_its_width(tmp_path):
    title = "Title " * 400  # far wider than the header: today's unbounded text, with or without the role
    plain = _render(tmp_path, _parts(declare=False), _source(title))

    assert _by_id(plain)["group-header:bus"].text == title
    assert _by_id(plain)["group-header:bus"].bounds[2] > _headers(plain)["bus"][2]
    assert _ellipsized(plain) == set()


def test_a_title_that_fits_beside_the_tab_is_not_shortened(tmp_path):
    tabbed = _render(tmp_path, _parts())

    assert [_by_id(tabbed)[f"group-header:{owner}"].text for owner in OWNERS] == ["Bus", "Payload", "Ground"]
    assert _ellipsized(tabbed) == set()


def test_the_block_size_defaults_to_the_header_and_an_explicit_one_is_kept(tmp_path):
    (tmp_path / "explicit").mkdir()
    default = _by_id(_render(tmp_path, _parts()))["group-tab:bus"]
    explicit = _render(tmp_path / "explicit", _parts(block=12))
    tab, header = _by_id(explicit)["group-tab:bus"], _headers(explicit)["bus"]

    assert default.bounds[3] == header[3] == 20.0
    assert tab.bounds == (header[0], header[1], 40.0, 12.0)


def test_a_tab_without_a_gap_touches_the_text(tmp_path):
    rendered = _render(tmp_path, _parts(gap=None))

    assert _by_id(rendered)["group-header:bus"].bounds[0] == pytest.approx(36 + 40)


def test_a_presentation_of_band_has_no_header_and_so_no_tab(tmp_path):
    parts = _parts()
    parts["view"]["body"]["grouping"]["presentation"] = "band"
    rendered = _render(tmp_path, parts)

    assert not [name for name in _by_id(rendered) if name.startswith(("group-tab:", "group-header:"))]


# --- failures ---------------------------------------------------------------------------------------------


@pytest.mark.parametrize("knobs, prop", [
    ({"inline": None}, "tabInlineSize"),
    ({"inline": 0}, "tabInlineSize"),
    ({"inline": -4}, "tabInlineSize"),
    ({"block": 0}, "tabBlockSize"),
    ({"block": 40}, "tabBlockSize"),
    ({"gap": -1}, "tabGap"),
    ({"inline": 1520, "gap": 8}, "tabInlineSize"),
])
def test_a_tab_that_cannot_be_drawn_is_a_declaration_error_naming_the_role_and_property(tmp_path, knobs, prop):
    with pytest.raises(RenderFailed) as caught:
        _render(tmp_path, _parts(**knobs))

    assert caught.value.code == "E_LAYOUT_GROUP_TAB_SIZE"
    assert caught.value.source_ref == f"/body/roles/group-tab/{prop}"
    assert caught.value.message.startswith(f"group-tab:{prop}:")


def test_a_header_one_unit_wider_than_the_tab_and_gap_is_accepted(tmp_path):
    header = _headers(_render(tmp_path, _parts(declare=False)))["bus"]
    (tmp_path / "edge").mkdir()

    rendered = _render(tmp_path / "edge", _parts(inline=header[2] - 1 - 6, gap=6))

    assert "group-tab:bus" in _by_id(rendered)


# --- the catalogue pattern, paint and the layered backgrounds --------------------------------------------


def test_the_pattern_is_attached_to_the_tab_rect_only_with_the_role_paint(tmp_path):
    rendered = _render(tmp_path, _parts())
    found = _by_id(rendered)

    for owner in OWNERS:
        tab = found[f"group-tab:{owner}"]
        assert tab.kind == "Rect" and tab.pattern is not None and tab.pattern.primitives
        assert (tab.paint.fill, tab.paint.stroke) == (YELLOW, DARK)
    assert [item.scene_id for item in rendered.surface.primitives
            if item.kind == "Rect" and item.pattern is not None and item.pattern.primitives
            ] == [f"group-tab:{owner}" for owner in OWNERS]
    assert rendered.artifact.content.decode().count("<pattern ") == len(OWNERS)  # one per tab: each has its own origin


def test_a_group_tint_leaves_the_tab_paint_alone(tmp_path):
    parts = _parts()
    parts["scheme"]["body"]["categories"]["series-1"] = "#1F3A66"
    parts["view"]["body"]["grouping"]["tint"] = {"scale": "series"}
    rendered = _render(tmp_path, parts)
    found = _by_id(rendered)

    assert found["group:bus"].paint.fill == "#1F3A66"
    assert all((found[f"group-tab:{owner}"].paint.fill, found[f"group-tab:{owner}"].paint.stroke) == (YELLOW, DARK)
               for owner in OWNERS)


def test_an_opaque_tab_inside_a_translucent_band_is_accepted(tmp_path):
    assert "group-tab:bus" in _by_id(_render(tmp_path, _parts(band_opacity=0.5, pattern=False)))


def test_a_translucent_tab_over_a_translucent_band_is_a_background_overlap(tmp_path):
    with pytest.raises(RenderFailed) as caught:
        _render(tmp_path, _parts(band_opacity=0.5, opacity=0.5, pattern=False))

    assert caught.value.code == "E_LAYOUT_BACKGROUND_OVERLAP"


def test_a_solid_outline_tab_is_a_rect_stroked_by_the_role(tmp_path):
    rendered = _render(tmp_path, _parts(treatment="outline", pattern=False, stroke="warning"))
    tab = _by_id(rendered)["group-tab:bus"]

    assert tab.kind == "Rect" and tab.pattern is None and tab.paint.stroke == YELLOW and tab.paint.fill is None


# --- adapters ---------------------------------------------------------------------------------------------


def test_svg_and_png_draw_the_tab_in_its_place_and_the_text_moves_off_it(tmp_path):
    (tmp_path / "plain").mkdir()
    tabbed = _render(tmp_path, _parts())
    plain = _render(tmp_path / "plain", _parts(declare=False))
    tab = _by_id(tabbed)["group-tab:bus"]

    svg = tabbed.artifact.content.decode()
    assert f'data-scene-id="{tab.scene_id}"' in svg and 'data-purpose="group-tab"' in svg
    after, before = _png(tabbed, tmp_path), _png(plain, tmp_path / "plain")
    x, y, width, height = (int(value) for value in tab.bounds)
    inside = after.crop((x, y, x + width, y + height)).getcolors(maxcolors=1 << 16)
    colours = {colour for _count, colour in inside}
    assert (0xFF, 0xC8, 0x57) in colours and (0x0B, 0x12, 0x20) in colours  # stripe and substrate, from the Theme
    assert before.crop((x, y, x + width, y + height)).getcolors(maxcolors=1 << 16) != inside


def test_typst_and_tikz_draw_a_solid_tab_as_a_plain_rect_at_its_place(tmp_path):
    surface = _render(tmp_path, _parts(pattern=False)).scene.surfaces[0]

    typst, tikz = render_v05_typst(surface), render_v05_tikz(surface)
    assert '#place(left: 36pt, top: 141.1pt)[#rect(width: 40pt, height: 20pt, fill: rgb("#FFC857"))]' in typst
    assert "% scene-id: group-tab:bus source-ref: bus" in tikz
    assert r"\path[fill=#FFC857] (36,141.1) rectangle (76,161.1);" in tikz
    assert typst.count('fill: rgb("#FFC857"))]') == tikz.count("fill=#FFC857") == len(OWNERS)


def test_typst_and_tikz_reject_a_patterned_tab_with_the_existing_capability_error(tmp_path):
    surface = _render(tmp_path, _parts()).scene.surfaces[0]

    for render in (render_v05_typst, render_v05_tikz):
        with pytest.raises(ValueError, match="E_VISUAL_CAPABILITY_UNSUPPORTED"):
            render(surface)


# --- the Theme schemas -------------------------------------------------------------------------------------


@pytest.mark.parametrize("schema", ["theme-v0.15.schema.yaml", "theme-v0.15.schema.yaml"])
def test_both_theme_schemas_accept_named_lengths_and_a_position_and_reject_literals(schema):
    validator = schema_validator(schema)

    def errors(**declared):
        theme = deepcopy(sr.bundle("control-room-dark")["theme"])
        theme["version"] = "chrona/theme/" + schema.split("-")[1].split(".schema")[0]
        theme["body"]["roles"]["group-tab"] = {"backgroundTreatment": "fill", "backgroundPaintOrder": 20, **declared}
        return [error for error in validator.iter_errors(theme) if "group-tab" in "/".join(map(str, error.absolute_path))]

    assert not errors(tabInlineSize="stroke-width", tabBlockSize="stroke-width", tabGap="stroke-width", tabPosition="end")
    assert not errors(tabPosition="start")
    for name in ("tabInlineSize", "tabBlockSize", "tabGap"):
        assert errors(**{name: 12})
    assert errors(tabPosition="middle")


# --- the contrast gate over and near the tab ---------------------------------------------------------------


def _errors(rendered, primitive_id: str) -> list:
    """The findings a Theme that declares decoration blocking (#995) would fail on; a warning by default."""
    return [item for item in _gate(rendered, primitive_id, "error") if item.severity == "error"]


def test_a_legible_tab_is_gated_on_the_band_under_it_and_raises_no_error(tmp_path):
    findings = _gate(_render(tmp_path, _parts()), "group-tab:bus")

    assert {item.code for item in findings} == {"E_SCENE_DECORATION_CONTRAST"}
    assert {item.severity for item in findings} == {"info"}
    # substrate on the band, ink on the substrate and ink on the band: neither channel hides the other
    assert {(item.paint_channel, item.ground_id, item.ground_kind) for item in findings} == {
        ("fill", "group:bus", "flat"), ("stroke", "group-tab:bus", "pattern-substrate"), ("stroke", "group:bus", "flat")}


def test_a_tab_whose_substrate_is_the_band_colour_is_a_gate_error(tmp_path):
    errors = _errors(_render(tmp_path, _parts(fill="surfaceRaised")), "group-tab:bus")

    assert [(item.paint_channel, item.ground_id) for item in errors] == [("fill", "group:bus")]


def test_a_pattern_ink_equal_to_its_substrate_is_a_gate_error(tmp_path):
    errors = _errors(_render(tmp_path, _parts(stroke="warning")), "group-tab:bus")

    assert {(item.paint_channel, item.ground_id, item.ground_kind) for item in errors} == {
        ("stroke", "group-tab:bus", "pattern-substrate")}


def test_an_end_tab_off_the_band_is_gated_on_the_canvas_it_stands_on(tmp_path):
    # The header spans table and timeline but the band only the table here, so an end tab stands on the canvas
    # and its ink (the canvas colour in this Theme) is invisible there: the gate says so.
    errors = _errors(_render(tmp_path, _parts(position="end")), "group-tab:bus")

    assert [(item.paint_channel, item.ground_id, item.ground_kind) for item in errors] == [("stroke", "canvas", "canvas")]


@pytest.mark.parametrize("position", ["start", "end"])
def test_the_header_text_beside_the_tab_is_still_gated_on_the_band_not_on_the_tab(tmp_path, position):
    findings = _gate(_render(tmp_path, _parts(position=position)), "group-header:bus")

    assert [(item.code, item.severity, item.floor, item.ground_id) for item in findings] == [
        ("E_SCENE_STATE_TEXT_CONTRAST", "info", 4.5, "group:bus")]


def _text_over_tab(tmp_path, *, fill=None, stroke=None) -> list:
    """The gate findings of the bus header text in a Scene whose tab is drawn under that text (no Layout path does)."""
    document = deepcopy(scene_document(_render(tmp_path, _parts()).scene))
    primitives = document["surfaces"][0]["primitives"]
    text = next(item for item in primitives if item["id"] == "group-header:bus")
    tab = next(item for item in primitives if item["id"] == "group-tab:bus")
    tab["bounds"] = dict(text["bounds"])
    tab["paint"].update({"fill": fill or tab["paint"]["fill"], "stroke": stroke or tab["paint"]["stroke"]})
    return [item for item in evaluate_scene_contrast(document) if item.primitive_id == "group-header:bus"]


def test_header_text_that_lay_on_the_tab_would_be_judged_on_the_tab_substrate(tmp_path):
    findings = _text_over_tab(tmp_path)  # light ink on the yellow substrate

    assert [(item.severity, item.ground_id, item.ground_kind) for item in findings] == [
        ("error", "group-tab:bus", "pattern-host-substrate")]


def test_header_text_that_lay_on_the_tab_would_be_judged_on_the_pattern_ink_too(tmp_path):
    ink = "#EAF0FA"  # the header ink
    findings = _text_over_tab(tmp_path, fill="#000000", stroke=ink)  # a legible substrate, an ink equal to the text

    assert [(item.severity, item.ground_id, item.ground_kind) for item in findings] == [
        ("error", "group-tab:bus", "pattern-host-ink")]
