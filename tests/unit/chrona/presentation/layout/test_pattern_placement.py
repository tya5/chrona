from decimal import Decimal

import pytest

from chrona.presentation.layout.model import LayoutError, Rect
from chrona.presentation.layout.pattern_placement import (
    PatternPathCommand,
    complete_pattern_placement,
)
from chrona.presentation.layout.surface_completion import complete_catalog_patterns
from chrona.presentation.layout.surface_quality import MarkPlacement, ShapePlacement


def test_pattern_placement_anchors_tile_at_translated_rect_top_left():
    bounds = Rect(Decimal("17.5"), Decimal("23"), Decimal("80"), Decimal("30"))
    pattern = {
        "tile": {"inlineSize": 8, "blockSize": 4},
        "angle": 45,
        "densityBasisPoints": 1250,
        "primitives": [{"kind": "circle", "cx": 4, "cy": 2, "radius": 1}],
    }

    placed = complete_pattern_placement(pattern, bounds)

    assert placed.region is bounds
    assert placed.clip is bounds
    assert placed.origin == (17.5, 23.0)
    assert (placed.tile_inline_size, placed.tile_block_size, placed.angle_degrees) == (8, 4, 45)
    assert placed.primitives[0].kind == "circle"
    assert placed.density_basis_points == 1250


def test_circle_operations_are_closed_optional_and_legacy_defaults_stay_implicit():
    pattern = {
        "tile": {"inlineSize": 8, "blockSize": 8}, "angle": 0,
        "densityBasisPoints": 1000,
        "primitives": [
            {"kind": "circle", "cx": 2, "cy": 3, "radius": 1},
            {"kind": "circle", "cx": 5, "cy": 3, "radius": 2,
             "fillChannel": "substrate", "strokeWidth": 0.5},
            {"kind": "circle", "cx": 7, "cy": 3, "radius": 1,
             "fillChannel": "none", "strokeWidth": 0.25},
        ],
    }
    circles = complete_pattern_placement(pattern, Rect(Decimal(0), Decimal(0), Decimal(20), Decimal(20))).primitives
    assert circles[0].fill_channel is None and circles[0].stroke_width is None
    assert (circles[1].fill_channel, circles[1].stroke_width) == ("substrate", 0.5)
    assert (circles[2].fill_channel, circles[2].stroke_width) == ("none", 0.25)


@pytest.mark.parametrize("primitive", [
    {"kind": "circle", "cx": 2, "cy": 3, "radius": 1, "fillChannel": "substratee"},
    {"kind": "circle", "cx": 2, "cy": 3, "radius": 1, "strokeWidth": 0},
    {"kind": "circle", "cx": 2, "cy": 3, "radius": 1, "strokeWidth": -1},
    {"kind": "circle", "cx": 2, "cy": 3, "radius": 1, "strokeWidth": 16.01},
    {"kind": "circle", "cx": 2, "cy": 3, "radius": 1, "extra": True},
])
def test_circle_operations_reject_unknown_or_invalid_values(primitive):
    with pytest.raises(LayoutError, match="E_PRESENTATION_PRIMITIVE_INVALID"):
        complete_pattern_placement({
            "tile": {"inlineSize": 8, "blockSize": 8}, "angle": 0,
            "densityBasisPoints": 1000, "primitives": [primitive],
        }, Rect(Decimal(0), Decimal(0), Decimal(20), Decimal(20)))


def test_pattern_placement_preserves_completed_rounded_rect_clip():
    bounds = Rect(Decimal(5), Decimal(7), Decimal(40), Decimal(20))
    pattern = {
        "tile": {"inlineSize": 8, "blockSize": 8},
        "angle": 0,
        "densityBasisPoints": 2500,
        "primitives": [{"kind": "rect", "x": 0, "y": 0,
                        "inlineSize": 8, "blockSize": 2}],
    }

    placed = complete_pattern_placement(pattern, bounds, corner_radius=6)

    assert placed.region == bounds
    assert placed.clip == bounds
    assert placed.corner_radius == 6


def test_pattern_path_close_is_retained_as_explicit_layout_command():
    pattern = {
        "tile": {"inlineSize": 8, "blockSize": 8},
        "angle": 0,
        "densityBasisPoints": 5000,
        "primitives": [{
            "kind": "path", "paint": "fill",
            "commands": [
                {"kind": "move", "points": [0, 0]},
                {"kind": "quadratic", "points": [4, 0, 8, 8]},
                {"kind": "close", "points": []},
            ],
        }],
    }

    placed = complete_pattern_placement(pattern, Rect(Decimal(0), Decimal(0), Decimal(20), Decimal(20)))

    assert placed.primitives[0].commands == (
        PatternPathCommand("move", ((0, 0),)),
        PatternPathCommand("quadratic", ((4, 0), (8, 8))),
        PatternPathCommand("close", ()),
    )


@pytest.mark.parametrize("corner_radius", [-1, 11])
def test_pattern_placement_rejects_invalid_completed_corner_radius(corner_radius):
    pattern = {
        "tile": {"inlineSize": 8, "blockSize": 8}, "angle": 0,
        "densityBasisPoints": 1250,
        "primitives": [{"kind": "rect", "x": 0, "y": 0,
                        "inlineSize": 8, "blockSize": 1}],
    }
    with pytest.raises(LayoutError, match="E_PRESENTATION_PRIMITIVE_INVALID"):
        complete_pattern_placement(pattern, Rect(Decimal(0), Decimal(0), Decimal(20), Decimal(20)), corner_radius)


def test_surface_pattern_binding_targets_only_allowlisted_completed_rects():
    token = {
        "kind": "catalog", "ref": "starter:hatch",
        "tile": {"inlineSize": 8, "blockSize": 8}, "angle": 0,
        "densityBasisPoints": 5000,
        "primitives": [{"kind": "rect", "x": 0, "y": 0,
                        "inlineSize": 8, "blockSize": 4}],
    }

    class Theme:
        def optional_pattern(self, role):
            return token if role == "annotation-highlight-box" else None

    highlight = ShapePlacement("highlight:one", "one", "Rect",
                               Rect(Decimal(3), Decimal(5), Decimal(40), Decimal(20)),
                               semantic_id="annotationHighlightBox", corner_radius=4)
    path = ShapePlacement("highlight:path", "one", "Path",
                          Rect(Decimal(3), Decimal(5), Decimal(0), Decimal(20)),
                          points=((3, 5), (3, 25)), semantic_id="annotationHighlightBox")
    not_allowlisted = ShapePlacement("planned:one", "one", "Rect",
                                     Rect(Decimal(3), Decimal(5), Decimal(40), Decimal(20)),
                                     semantic_id="planned")

    placements = complete_catalog_patterns((), (highlight, path, not_allowlisted), Theme())

    assert len(placements) == 1
    assert placements[0].placement_id == "highlight:one"
    assert placements[0].pattern.origin == (3.0, 5.0)
    assert placements[0].pattern.corner_radius == 4


def test_shape_patterns_precede_span_mark_patterns_and_point_marks_get_none():
    """The final pattern pass reads completed shapes first, then span marks, in that order (#592 I592-6)."""
    token = {
        "kind": "catalog", "ref": "starter:hatch",
        "tile": {"inlineSize": 8, "blockSize": 8}, "angle": 0,
        "densityBasisPoints": 5000,
        "primitives": [{"kind": "rect", "x": 0, "y": 0, "inlineSize": 8, "blockSize": 4}],
    }

    class Theme:
        def optional_pattern(self, role):
            return token if role in {"missing-actual", "annotation-highlight-box"} else None

    bounds = Rect(Decimal(3), Decimal(5), Decimal(40), Decimal(20))
    span = MarkPlacement("missing-actual:one", "one", bounds, (3.0, 15.0), (43.0, 15.0),
                         mark_shape="span", semantic_id="missing-actual")
    point = MarkPlacement("missing-actual:two", "two", bounds, (3.0, 15.0), (3.0, 15.0),
                          mark_shape="point", semantic_id="missing-actual")
    highlight = ShapePlacement("highlight:one", "one", "Rect", bounds, semantic_id="annotationHighlightBox")

    placements = complete_catalog_patterns((span, point), (highlight,), Theme())

    assert [item.placement_id for item in placements] == ["highlight:one", "missing-actual:one"]
