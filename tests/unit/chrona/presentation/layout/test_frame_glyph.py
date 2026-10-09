"""Generic frame runs use synthetic decisions, never a project-specific target."""
from decimal import Decimal
from pathlib import Path

import pytest
import yaml

from chrona.presentation.layout.frame_glyph import complete_frame_glyphs, frame_glyph_boxes
from chrona.presentation.layout.model import LayoutDecision, Rect, RegionFrame
from chrona.presentation.color_scheme import resolve_theme
from chrona.presentation.model.theme_tokens import ThemeTokenError, ThemeTokenView
from tests.support import synthetic_review as sr

D = Decimal


class Tokens:
    def __init__(self, roles=None, *, size="10", pitch="20", symbol=None, glyph=None):
        self.roles = {"frame-glyph"} if roles is None else roles
        self.size, self.pitch = D(size), D(pitch)
        self.value = symbol or {"shape": {"catalog": "local:bulb"}}
        self.glyph = glyph or {"viewport": {"inlineSize": 10, "blockSize": 10},
                               "parts": [{"data": "M0 0L10 0L10 10L0 10Z", "paint": "fill"}]}

    def has_role(self, role):
        return role in self.roles

    def number(self, role, prop):
        return {"glyphSize": self.size, "glyphPitch": self.pitch}[prop]

    def symbol(self, role):
        return self.value

    def catalog_glyph(self, reference):
        assert reference == "local:bulb"
        return self.glyph


def decision(name="title", *, width="110", height="70", paint=None, populated=True, inset="0"):
    return LayoutDecision(name, "slot", Rect(D(20), D(30), D(width), D(height)),
                          frame=RegionFrame(D(inset), populated, paint))


def test_absent_roles_and_absent_declarations_are_the_identical_noop():
    bare = LayoutDecision("bare", "row", Rect(D(0), D(0), D(100), D(100)))
    assert complete_frame_glyphs(Tokens(roles=set()), (decision(),)) == complete_frame_glyphs(Tokens(), (bare,))


def test_four_unique_corners_then_clockwise_interiors_at_exact_pitch():
    boxes = frame_glyph_boxes(Rect(D(20), D(30), D(110), D(70)), D(10), D(20))
    assert len(boxes) == 16  # 2*5 horizontal + 2*3 vertical intervals
    assert [(box.inline, box.block) for box in boxes[:4]] == [(20, 30), (120, 30), (120, 90), (20, 90)]
    assert len({(box.inline, box.block) for box in boxes}) == len(boxes)
    assert [box.inline for box in boxes[4:8]] == [40, 60, 80, 100]
    assert [box.block for box in boxes[8:10]] == [50, 70]
    assert [box.inline for box in boxes[10:14]] == [100, 80, 60, 40]
    assert [box.block for box in boxes[14:]] == [70, 50]


def test_nondividing_length_distributes_remainder_in_equal_spacing():
    boxes = frame_glyph_boxes(Rect(D(0), D(0), D(117), D(73)), D(10), D(20))
    assert len(boxes) == 16
    assert [box.inline for box in boxes[4:8]] == [D("21.4"), D("42.8"), D("64.2"), D("85.6")]
    assert [box.block for box in boxes[8:10]] == [21, 42]
    assert all(box.inline + box.inline_size <= 117 and box.block + box.block_size <= 73 for box in boxes)


def test_minimum_fitting_frame_has_exactly_four_corners():
    assert len(frame_glyph_boxes(Rect(D(0), D(0), D(30), D(30)), D(10), D(20))) == 4


@pytest.mark.parametrize("width,height", [("29.99", "30"), ("30", "29.99"), ("0", "70")])
def test_too_small_omits_whole_border(width, height):
    result = complete_frame_glyphs(Tokens(), (decision(width=width, height=height),))
    assert not result.shapes and not result.slots and not result.extents
    assert result.diagnostics == ("I_LAYOUT_FRAME_GLYPH_OMITTED:title:too-small",)


def test_no_content_omits_whole_border():
    result = complete_frame_glyphs(Tokens(), (decision(populated=False),))
    assert result.diagnostics == ("I_LAYOUT_FRAME_GLYPH_OMITTED:title:no-content",)
    assert not result.shapes


def test_generic_named_paint_selection_is_independent_and_never_falls_back():
    nodes = (decision("container", paint="marquee"), decision("other", paint="missing"), decision("title"))
    result = complete_frame_glyphs(Tokens(roles={"frame-glyph-marquee"}), nodes)
    assert [shape.placement_id for shape in result.shapes] == ["frame-glyph:container"]
    assert result.shapes[0].visual_role == "frame-glyph-marquee"


def test_one_closed_batch_is_a_whole_border_not_an_adapter_fit_request():
    node = decision(inset="2")
    result = complete_frame_glyphs(Tokens(), (node,))
    shape, = result.shapes
    assert (shape.kind, shape.semantic_id, shape.paint_order) == ("Glyph", "frameGlyph", 0)
    assert len(shape.symbol_parts) == 12
    assert shape.bounds == Rect(D(22), D(32), D(106), D(66))
    assert shape.bounds == result.slots[0].bounds == result.extents[0]
    assert shape.source_ref == "layout-node:title"
    assert node.bounds == Rect(D(20), D(30), D(110), D(70))  # no feedback into content geometry
    assert result == complete_frame_glyphs(Tokens(), (node,))


def test_catalogue_stroke_envelope_stays_inside_the_declared_inset():
    glyph = {"viewport": {"inlineSize": 10, "blockSize": 10}, "parts": [
        {"data": "M0 0L10 0L10 10L0 10Z", "paint": "fill"},
        {"data": "M0 0L10 0L10 10L0 10Z", "paint": "stroke", "strokeWidth": 2,
         "lineCap": "round", "lineJoin": "round"}]}
    result = complete_frame_glyphs(Tokens(symbol={"shape": {"catalog": "local:bulb"}}, glyph=glyph),
                                   (decision(inset="4"),))
    shape, = result.shapes
    assert len(shape.symbol_parts) == 24
    corners = [part for part in shape.symbol_parts[:8] if part.paint_mode == "stroke"]
    assert len(corners) == 4 and all(part.stroke_width == 2 for part in corners)
    first = corners[0]
    assert first.commands[0].points == ((25.0, 35.0),)
    assert min(point[0] for part in shape.symbol_parts for command in part.commands for point in command.points) - 1 == 24


@pytest.mark.parametrize("cap,join,envelope", [("round", "round", 1), ("square", "bevel", 2),
                                             ("butt", "miter", 20)])
def test_stroke_envelope_accounts_for_cap_diagonal_and_target_neutral_miter_bound(cap, join, envelope):
    glyph = {"viewport": {"inlineSize": 10, "blockSize": 10}, "parts": [
        {"data": "M0 0L10 0L10 10L0 10Z", "paint": "stroke", "strokeWidth": 2,
         "lineCap": cap, "lineJoin": join}]}
    result = complete_frame_glyphs(Tokens(glyph=glyph), (decision(),))
    assert result.shapes[0].symbol_parts[0].commands[0].points == ((20 + envelope, 30 + envelope),)


@pytest.mark.parametrize("symbol", [{"shape": "square"}, {"shape": "glyph", "viewBox": [10, 10], "parts": []}])
def test_catalogue_consumer_rejects_non_catalogue_symbols_at_its_binding(symbol):
    with pytest.raises(ThemeTokenError) as found:
        complete_frame_glyphs(Tokens(symbol=symbol), (decision(),))
    assert found.value.path == "/body/roles/frame-glyph/symbol"


@pytest.mark.parametrize("size,pitch,prop", [("0", "20", "glyphSize"), ("-1", "20", "glyphSize"),
                                          ("NaN", "20", "glyphSize"), ("10", "Infinity", "glyphPitch"),
                                          ("10", "0", "glyphPitch"), ("10", "9", "glyphPitch")])
def test_invalid_geometry_has_exact_binding_pointer(size, pitch, prop):
    with pytest.raises(ThemeTokenError) as found:
        complete_frame_glyphs(Tokens(size=size, pitch=pitch), (decision(),))
    assert found.value.diagnostic_id == "E_THEME_TOKEN_TYPE"
    assert found.value.path == f"/body/roles/frame-glyph/{prop}"


def test_reusable_marquee_yaml_completes_the_actual_packaged_bulb_parts():
    root = Path(__file__).resolve().parents[5]
    declaration = yaml.safe_load((root / "tests/fixtures/surface-decoration/marquee-glyph-frame.yaml").read_text())
    catalogue = yaml.safe_load((root / "src/chrona/resources/icons/chrona-target-parts-v2026-10-09.yaml").read_text())
    parts = sr.bundle()
    theme_patch, scheme_patch = declaration["themePatch"], declaration["schemePatch"]
    parts["theme"]["version"] = theme_patch["version"]
    parts["theme"]["body"]["values"].update(theme_patch["values"])
    parts["theme"]["body"]["roles"].update(theme_patch["roles"])
    parts["theme"]["body"]["colorBindings"].update(theme_patch["colorBindings"])
    parts["scheme"]["body"]["categories"].update(scheme_patch["categories"])
    resolved = resolve_theme(parts["theme"], parts["scheme"], scheme_content_identity="fixture")
    tokens = ThemeTokenView(resolved,
                            catalog_glyphs={"chrona-target-parts:bulb": catalogue["body"]["glyphs"]["bulb"]})
    result = complete_frame_glyphs(tokens, (decision(paint="marquee", width="800", height="80", inset="4"),))
    shape, = result.shapes
    assert shape.visual_role == "frame-glyph-marquee"
    assert len(shape.symbol_parts) > 8 and len(shape.symbol_parts) % 2 == 0
    assert {part.paint_mode for part in shape.symbol_parts} == {"fill", "stroke"}
    assert all(part.line_cap == "round" for part in shape.symbol_parts if part.paint_mode == "stroke")
    assert result == complete_frame_glyphs(tokens, (decision(paint="marquee", width="800", height="80", inset="4"),))
