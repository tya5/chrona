from __future__ import annotations

from chrona.presentation.layout.mark_geometry import (
    SymbolPartPlacement,
    complete_point_outline,
)
from chrona.presentation.layout.model import LayoutError
from chrona.presentation.layout.surface_quality import PathCommand as C


def _rect(x0: float, y0: float, x1: float, y1: float):
    points = ((x0, y0), (x1, y0), (x1, y1), (x0, y1))
    return (C("move", (points[0],)), *(C("line", (point,)) for point in points[1:]),
            C("line", (points[0],)))


class _Tokens:
    def __init__(self, *, bindings=("stroke", "strokeWidth"), width=2.0, pattern=None):
        self.bindings = set(bindings)
        self.width = width
        self.pattern = pattern
        self.binding_queries = []
        self.pattern_queries = []
        self.number_queries = []
        self.color_queries = []

    def has_binding(self, role, property_name):
        self.binding_queries.append((role, property_name))
        return property_name in self.bindings

    def optional_pattern(self, role):
        self.pattern_queries.append(role)
        return self.pattern

    def optional_number(self, role, property_name):
        self.number_queries.append((role, property_name))
        return self.width

    def color(self, role, property_name="stroke"):
        self.color_queries.append((role, property_name))
        raise AssertionError("Layout must not resolve the outline color")


def test_filled_glyph_appends_union_stroke_and_preserves_original_parts_exactly():
    fill = SymbolPartPlacement(_rect(0, 0, 8, 8), paint_mode="fill", paint_color="#eeee00")
    intrinsic = SymbolPartPlacement(_rect(20, 0, 28, 8), paint_mode="stroke",
                                    paint_color="#123456", stroke_width=0.75,
                                    line_cap="round", line_join="bevel")
    parts = (fill, intrinsic)
    tokens = _Tokens()

    completed = complete_point_outline(parts, paint_role="gate", theme_tokens=tokens)

    assert completed[:len(parts)] == parts
    assert completed[0] is fill and completed[1] is intrinsic
    assert len(completed) == 3
    assert completed[-1].paint_mode == "stroke"
    assert completed[-1].stroke_width == 2.0
    assert completed[-1].paint_color is None
    assert completed[-1].commands == fill.commands
    assert tokens.binding_queries == [("gate", "stroke"), ("gate", "strokeWidth")]
    assert tokens.number_queries == [("gate", "strokeWidth")]
    assert tokens.color_queries == []


def test_builtin_and_stroke_only_symbols_are_exact_bypasses():
    builtin = (SymbolPartPlacement(_rect(0, 0, 4, 4)),)
    stroke_only = (SymbolPartPlacement(_rect(0, 0, 4, 4), paint_mode="stroke", stroke_width=1),)
    for parts in (builtin, stroke_only):
        tokens = _Tokens()
        assert complete_point_outline(parts, paint_role="gate", theme_tokens=tokens) is parts
        assert tokens.binding_queries == []
        assert tokens.number_queries == []
        assert tokens.color_queries == []


def test_missing_either_binding_is_an_exact_bypass_without_role_fallback():
    fill = SymbolPartPlacement(_rect(0, 0, 4, 4), paint_mode="fill")
    parts = (fill,)
    for bindings in (("stroke",), ("strokeWidth",), ()):
        tokens = _Tokens(bindings=bindings)
        assert complete_point_outline(parts, paint_role="planned", theme_tokens=tokens) is parts
        assert all(role == "planned" for role, _property in tokens.binding_queries)
        assert tokens.number_queries == []
        assert tokens.pattern_queries == []
        assert tokens.color_queries == []


def test_outline_pattern_keeps_original_parts_and_never_resolves_outline_width():
    fill = SymbolPartPlacement(_rect(0, 0, 4, 4), paint_mode="fill")
    parts = (fill,)
    tokens = _Tokens(pattern={"kind": "outline"})

    assert complete_point_outline(parts, paint_role="milestone", theme_tokens=tokens) is parts
    assert tokens.pattern_queries == ["milestone"]
    assert tokens.number_queries == []
    assert tokens.color_queries == []


def test_nonpositive_stroke_width_is_an_exact_bypass(monkeypatch):
    fill = SymbolPartPlacement(_rect(0, 0, 4, 4), paint_mode="fill")
    parts = (fill,)
    for width in (0, -1):
        tokens = _Tokens(width=width)
        monkeypatch.setattr("chrona.presentation.layout.mark_geometry.union_filled_contours",
                            lambda _fills: (_ for _ in ()).throw(AssertionError("union must be bypassed")))
        assert complete_point_outline(parts, paint_role="legend", theme_tokens=tokens) is parts
        assert tokens.number_queries == [("legend", "strokeWidth")]
        assert tokens.color_queries == []


def test_nonfinite_width_has_bounded_layout_diagnostic_at_concrete_role_pointer():
    fill = SymbolPartPlacement(_rect(0, 0, 4, 4), paint_mode="fill")
    tokens = _Tokens(width=float("inf"))

    try:
        complete_point_outline((fill,), paint_role="gate", theme_tokens=tokens)
    except LayoutError as error:
        assert error.diagnostic_id == "E_LAYOUT_POINT_OUTLINE_INVALID"
        assert error.path == "/body/roles/gate/strokeWidth"
        assert error.detail == "stage=input; reason=nonfinite; operand=strokeWidth"
        assert len(str(error)) < 128
    else:
        raise AssertionError("nonfinite width must be rejected")


def test_contour_union_failure_maps_to_bounded_layout_error_without_fallback(monkeypatch):
    fill = SymbolPartPlacement(_rect(0, 0, 4, 4), paint_mode="fill")

    def fail(_fills):
        from chrona.presentation.layout.filled_contour import ContourUnionError
        raise ContourUnionError("union", "operation-failed")

    monkeypatch.setattr("chrona.presentation.layout.mark_geometry.union_filled_contours", fail)
    tokens = _Tokens()
    try:
        complete_point_outline((fill,), paint_role="gate", theme_tokens=tokens)
    except LayoutError as error:
        assert error.diagnostic_id == "E_LAYOUT_POINT_OUTLINE_INVALID"
        assert error.path == "/body/roles/gate/strokeWidth"
        assert error.detail == "stage=union; reason=operation-failed; fillParts=1"
        assert len(str(error)) < 128
        assert tokens.number_queries == [("gate", "strokeWidth")]
        assert tokens.color_queries == []
    else:
        raise AssertionError("invalid contour must not fall back to the raw path")
