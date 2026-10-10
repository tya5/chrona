from dataclasses import replace
from decimal import Decimal

import pytest

from chrona.presentation.layout.model import LayoutError, Rect
from chrona.presentation.layout.pattern_placement import PatternPathCommand, complete_pattern_placement
from chrona.presentation.layout.surface_completion import complete_catalog_patterns
from chrona.presentation.layout.surface_marks import complete_progress_shape
from chrona.presentation.layout.surface_quality import MarkPlacement, PaintClip, PathCommand, ShapePlacement, SurfacePlacement


TOKEN = {"kind": "catalog", "tile": {"inlineSize": 8, "blockSize": 8}, "angle": 0,
         "densityBasisPoints": 5000,
         "primitives": [{"kind": "rect", "x": 0, "y": 0, "inlineSize": 8, "blockSize": 4}]}
BOUNDS = Rect(Decimal(10), Decimal(20), Decimal(40), Decimal(10))
CONTOUR = (PathCommand("move", ((10, 20),)), PathCommand("line", ((50, 20),)),
           PathCommand("line", ((50, 30),)), PathCommand("line", ((10, 30),)),
           PathCommand("line", ((12, 25),)), PathCommand("line", ((10, 20),)))


class Theme:
    def optional_pattern(self, role):
        return TOKEN


def _shape(role="summaryBar"):
    return ShapePlacement("cut", "object", "Symbol", BOUNDS, semantic_id=role,
        path_commands=CONTOUR, paint_clip=PaintClip((10, 20, 40, 10)), pattern_origin=(-30, 20))


@pytest.mark.parametrize("role", ["progressFill", "summaryBar"])
def test_cut_symbol_pattern_retains_original_phase_and_exact_closed_visible_contour(role):
    shape = _shape(role)
    patterns = complete_catalog_patterns((), (shape,), Theme())
    assert len(patterns) == 1
    pattern = patterns[0].pattern
    assert pattern.origin == (-30, 20) and pattern.region == pattern.clip == BOUNDS
    assert pattern.cut_contour == tuple(PatternPathCommand(command.kind, command.points) for command in CONTOUR)
    SurfacePlacement(shapes=(shape,), patterns=patterns).assert_valid()


def test_cut_missing_actual_span_uses_same_phase_contract_without_admitting_other_roles():
    mark = MarkPlacement("cut", "object", BOUNDS, None, (50, 25), semantic_id="missing-actual",
        path_commands=CONTOUR, paint_clip=PaintClip((10, 20, 40, 10)), pattern_origin=(-30, 20))
    patterns = complete_catalog_patterns((mark,), (), Theme())
    assert patterns[0].pattern.origin == (-30, 20)
    SurfacePlacement(marks=(mark,), patterns=patterns).assert_valid()
    assert complete_catalog_patterns((replace(mark, semantic_id="planned"),), (), Theme()) == ()


def test_arbitrary_glyph_or_missing_cut_provenance_is_not_a_pattern_authoring_site():
    assert complete_catalog_patterns((), (_shape("annotationHighlightBox"),), Theme()) == ()
    assert complete_catalog_patterns((), (replace(_shape(), paint_clip=None),), Theme()) == ()
    with pytest.raises(LayoutError, match="missing-original-origin"):
        complete_catalog_patterns((), (replace(_shape(), pattern_origin=None),), Theme())


@pytest.mark.parametrize("contour", [CONTOUR[:-1], (PathCommand("move", ((9, 20),)), *CONTOUR[1:])])
def test_open_or_outside_cut_contours_fail_closed(contour):
    with pytest.raises(LayoutError, match="E_PRESENTATION_PRIMITIVE_INVALID"):
        complete_pattern_placement(TOKEN, BOUNDS, origin=(-30, 20),
            cut_contour=tuple(PatternPathCommand(command.kind, command.points) for command in contour))


def test_plain_rect_cannot_change_repeat_origin_and_plain_identity_is_unchanged():
    with pytest.raises(LayoutError, match="E_PRESENTATION_PRIMITIVE_INVALID"):
        complete_pattern_placement(TOKEN, BOUNDS, origin=(-30, 20))
    ordinary = complete_pattern_placement(TOKEN, BOUNDS)
    assert ordinary.origin == (10, 20) and ordinary.cut_contour == ()


def test_pattern_cannot_be_rebound_to_a_different_original_phase_or_contour():
    shape = _shape()
    patterns = complete_catalog_patterns((), (shape,), Theme())
    with pytest.raises(ValueError, match="E_LAYOUT_PATTERN_REGION_INVALID"):
        SurfacePlacement(shapes=(replace(shape, pattern_origin=(0, 20)),), patterns=patterns).assert_valid()


def test_progress_phase_is_its_original_inset_anchor_not_the_visible_host_origin():
    original_bounds = Rect(Decimal(-30), Decimal(20), Decimal(80), Decimal(10))
    original = MarkPlacement("planned:x", "x", original_bounds, (-30, 25), (50, 25))
    visible = replace(original, bounds=BOUNDS, start_port=None, path_commands=CONTOUR,
                      paint_clip=PaintClip((10, 20, 40, 10)), pattern_origin=(-30, 20))
    progress = complete_progress_shape(visible, original_host=original, fraction=.75,
                                      inset_ratio=Decimal('.1'), radius_ratio=Decimal(0))
    assert progress is not None and progress.kind == "Symbol"
    assert progress.pattern_origin == (-29, 21)
    assert complete_catalog_patterns((), (progress,), Theme())[0].pattern.origin == (-29, 21)


def test_real_lane_composition_completes_cut_progress_pattern_from_original_geometry(monkeypatch):
    from datetime import date
    from chrona.presentation.layout.surface_composer import compose_surface_layout
    from chrona.presentation.layout.surface_lanes import preflight_fixed_lane_layout
    from tests.unit.chrona.presentation.layout.test_lane_item_footprints import _window_footprint_fixture
    from tests.unit.chrona.presentation.layout.test_window_lane_completion import _request
    projection, _, _ = _window_footprint_fixture()
    across = replace(projection.items[1], planned={"start": date(2026, 1, 1), "end": date(2026, 1, 9)},
                     planned_progress=.6)
    items = (projection.items[0], across, projection.items[2])
    projection = replace(projection, items=items,
        rows=tuple(replace(row, items=(item,)) for row, item in zip(projection.rows, items, strict=True)),
        lane_rows=(replace(projection.lane_rows[0], items=items),))
    request = _request(projection=projection)
    tokens = type(request.theme_tokens)
    original_pattern = tokens.optional_pattern
    monkeypatch.setattr(tokens, "optional_pattern", lambda self, role:
        TOKEN if role == "progress-fill" else original_pattern(self, role))
    monkeypatch.setattr(tokens, "progress_track", lambda self, role: (Decimal('.1'), Decimal(0)))
    request = replace(request, surface_content=replace(request.surface_content, progress_fill_source="planned"))
    preflight = preflight_fixed_lane_layout(projection=projection, layout_manifest=request.layout_manifest,
        surface_content=request.surface_content, theme_tokens=request.theme_tokens,
        metric_values=request.measured_sources.metric_values, icon_assets=request.icon_assets,
        visual_requests=request.visual_requests, font_metrics=request.font_metrics)
    placement = compose_surface_layout(replace(request, fixed_lane_preflight=preflight)).placement
    progress = next(shape for shape in placement.shapes if shape.semantic_id == "progressFill")
    pattern = next(item.pattern for item in placement.patterns if item.placement_id == progress.placement_id)
    assert pattern.origin == progress.pattern_origin
    assert pattern.origin[0] < float(progress.bounds.inline)
    assert pattern.region == pattern.clip == progress.bounds and pattern.cut_contour
    placement.assert_valid()
