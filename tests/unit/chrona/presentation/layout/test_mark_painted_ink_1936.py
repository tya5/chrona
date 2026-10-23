"""Layout facets use the same effective paint and profile admission as Scene."""
from types import SimpleNamespace

import pytest

from chrona.presentation.layout.lane_mark_facets import _mark_facets
from chrona.presentation.layout.lane_projection import LaneProjectionInstance
from chrona.presentation.layout.mark_geometry import SymbolPartPlacement
from chrona.presentation.layout.model import LayoutError, Rect
from chrona.presentation.layout.obstacles import obstacle_envelope
from chrona.presentation.layout.path_ink import stroked_path_bounds
from chrona.presentation.layout.surface_quality import MarkPlacement, PaintClip, PathCommand as C
from chrona.presentation.model.theme_tokens import ThemeTokenView
from chrona.presentation.scene.paint import _stroke_finish
from chrona.presentation.scene.visual_capabilities import (
    BASELINE_PROFILE, SVG_PROFILE, paint_witness_capabilities, resolve_visual_profile,
)


LINE = (C("move", ((0, 0),)), C("line", ((10, 0),)))


def _theme(*, outline=True, finish=False, fidelity="decorative-optional"):
    values = {
        "ink": {"type": "color", "value": "#112233"},
        "width": {"type": "number", "value": 2},
        "outline": {"type": "pattern", "value": {"kind": "outline"}},
        "cap": {"type": "lineCap", "value": "square"},
        "join": {"type": "lineJoin", "value": "bevel"},
        "fidelity": {"type": "fidelity", "value": fidelity},
    }
    role = {"fill": "ink", "stroke": "ink", "strokeWidth": "width"}
    if outline:
        role["pattern"] = "outline"
    if finish:
        role.update(strokeLineCap="cap", strokeLineJoin="join", strokeFinishFidelity="fidelity")
    return ThemeTokenView({"version": "chrona/resolved-theme/v0.2", "kind": "resolved-theme",
                           "body": {"values": values, "roles": {"planned": role}, "metrics": {}}})


def _facet(part, theme, profile=SVG_PROFILE, *, clip=None):
    item = SimpleNamespace(item_id="gate", object_id="gate", source_kind="primary")
    instance = LaneProjectionInstance("row", "gate", "gate", "primary")
    mark = MarkPlacement("planned:row:gate", "gate", Rect(0, 0, 20, 20), None, None,
                         mark_shape="point", semantic_id="planned", symbol_parts=(part,), paint_clip=clip)
    return _mark_facets(item, instance, mark, theme, paint_capabilities=paint_witness_capabilities(
        resolve_visual_profile(profile, "svg")))[0]


@pytest.mark.parametrize("profile,bounds,omitted", [
    (BASELINE_PROFILE, (0, -1, 10, 1), True),
    (SVG_PROFILE, (-1, -1, 11, 1), False),
])
def test_role_finish_admission_matches_scene_and_inherited_outline(profile, bounds, omitted):
    theme = _theme(finish=True)
    facet = _facet(SymbolPartPlacement(LINE), theme, profile)
    assert obstacle_envelope(facet.visible_footprint) == pytest.approx(bounds)
    finish, actual_omission = _stroke_finish(theme, "planned", resolve_visual_profile(profile, "svg"))
    assert actual_omission is omitted
    assert (finish is None) is omitted
    assert facet.glyph_part_projection.paint_mode is None
    assert facet.glyph_part_projection.stroke_width is None


def test_required_finish_unsupported_has_existing_pointed_diagnostic():
    with pytest.raises(LayoutError) as error:
        _facet(SymbolPartPlacement(LINE), _theme(finish=True, fidelity="required"), BASELINE_PROFILE)
    assert (error.value.diagnostic_id, error.value.path) == (
        "E_VISUAL_CAPABILITY_UNSUPPORTED", "/body/roles/planned/strokeLineCap")


def test_intrinsic_catalog_stroke_width_and_finish_override_role_channels():
    part = SymbolPartPlacement(LINE, paint_mode="stroke", stroke_width=6,
                               line_cap="square", line_join="round")
    facet = _facet(part, _theme(outline=False))
    assert obstacle_envelope(facet.visible_footprint) == pytest.approx((-3, -3, 13, 3))
    assert facet.glyph_part_projection.stroke_width == 6


def test_fill_curve_control_hull_is_not_a_painted_ink_requirement():
    curve = (C("move", ((0, 0),)), C("quadratic", ((10, 20), (20, 0))),
             C("line", ((0, 0),)))
    facet = _facet(SymbolPartPlacement(curve, paint_mode="fill"), _theme(outline=False))
    assert facet.primitive_bounds == (0, 0, 20, 20)
    assert obstacle_envelope(facet.visible_footprint) == pytest.approx((0, 0, 20, 10))


def test_visible_outline_is_clipped_without_changing_projection_bounds():
    rectangle = (C("move", ((0, 0),)), C("line", ((10, 0),)), C("line", ((10, 10),)),
                 C("line", ((0, 10),)), C("line", ((0, 0),)))
    facet = _facet(SymbolPartPlacement(rectangle), _theme(), clip=PaintClip((0, 0, 6, 6)))
    assert facet.primitive_bounds == (0, 0, 10, 10)
    assert obstacle_envelope(facet.visible_footprint) == (0, 0, 6, 6)


def test_move_only_subpath_does_not_create_ink_or_crash():
    commands = (C("move", ((-100, -100),)), *LINE, C("move", ((100, 100),)))
    assert stroked_path_bounds(commands, 2) == (0, -1, 10, 1)
    with pytest.raises(ValueError, match="no painted contour"):
        stroked_path_bounds((C("move", ((0, 0),)),), 2)
