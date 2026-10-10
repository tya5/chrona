"""Pattern/subject contact must meet the filled cut host, not its envelope."""
from copy import deepcopy

import pytest

from chrona.presentation.scene.contrast_policy import evaluate_scene_contrast
from chrona.presentation.scene.ink_touch import InkTouchError, fill_touches, filled_trapezoids
from chrona.presentation.scene.pattern_ink import pattern_ink_touches


def _outline(points):
    return [{"kind": "move" if index == 0 else "line", "points": [list(point)]}
            for index, point in enumerate(points)]


CONTOUR = _outline(((30, 20), (90, 20), (90, 60), (30, 60),
                    (30, 50), (38, 40), (30, 30), (30, 20)))
REGION = {"inline": 30, "block": 20, "inlineSize": 60, "blockSize": 40}


def _host(*, circle=(23, 20, 1), outline=CONTOUR, angle=0):
    return {"id": "cut", "kind": "Symbol", "sourceRef": "task", "sourceKind": "object",
            "purpose": "progress-fill", "visualRole": "progress-fill", "bounds": dict(REGION),
            "paintOrder": 10, "symbol": {"outline": deepcopy(outline)},
            "paintClip": {"bounds": dict(REGION)},
            "paint": {"stroke": "#000000", "opacity": 1},
            "pattern": {"tileInlineSize": 100, "tileBlockSize": 100, "angleDegrees": angle,
                        "densityBasisPoints": 1250, "origin": [10, 20],
                        "regionBounds": dict(REGION), "clipBounds": dict(REGION), "cornerRadius": 0,
                        "primitives": [{"kind": "circle", "cx": circle[0], "cy": circle[1], "radius": circle[2]}]}}


def test_notch_rejects_ink_even_when_subject_also_meets_visible_host():
    host = _host()
    bounds = (30, 35, 20, 10)
    assert fill_touches(CONTOUR, bounds)
    rectangle = deepcopy(host)
    rectangle["kind"] = "Rect"
    assert pattern_ink_touches(rectangle, bounds)
    assert not pattern_ink_touches(host, bounds)
    assert pattern_ink_touches(_host(circle=(45, 20, 1)), (54, 39, 2, 2))


@pytest.mark.parametrize("opposite,expected", [(True, False), (False, True)])
def test_nonzero_winding_preserves_holes_and_overlapping_fill(opposite, expected):
    points = ((50, 35), (50, 45), (60, 45), (60, 35), (50, 35))
    if not opposite:
        points = tuple(reversed(points))
    host = _host(circle=(45, 20, 1), outline=CONTOUR + _outline(points))
    assert pattern_ink_touches(host, (54, 39, 2, 2)) is expected


@pytest.mark.parametrize("angle", [0, 45, 90])
def test_host_query_is_clipped_before_tile_rotation(angle):
    host = _host(angle=angle)
    host["pattern"]["primitives"] = [{"kind": "rect", "x": 0, "y": 0,
                                        "inlineSize": 100, "blockSize": 100}]
    assert not pattern_ink_touches(host, (31, 39, 1, 1))
    assert pattern_ink_touches(host, (39, 39, 1, 1))
    assert pattern_ink_touches(host, (38, 40, 0, 0))  # closed contour touch


@pytest.mark.parametrize("outline", [CONTOUR[:-1], [{"kind": "move", "points": [[30, 20]]}],
                                      CONTOUR + [{"kind": "move", "points": [[35, 25]]}],
                                      CONTOUR + _outline(((95, 25), (96, 25), (96, 26), (95, 25)))])
def test_unreadable_or_outside_contour_fails_closed_even_for_disjoint_query(outline):
    with pytest.raises(InkTouchError):
        pattern_ink_touches(_host(outline=outline), (-100, -100, 1, 1))


def test_convex_cells_match_nonzero_fill_at_grid_samples_including_self_crossing():
    crossing = _outline(((40, 25), (80, 55), (40, 55), (80, 25), (40, 25)))
    for outline in (CONTOUR, crossing):
        cells = filled_trapezoids(outline)
        for y in range(21, 60, 2):
            for x in range(31, 90, 2):
                represented = any(fill_touches(_outline((*cell, cell[0])), (x, y, 0, 0)) for cell in cells)
                assert represented == fill_touches(outline, (x, y, 0, 0)), (x, y)


def test_opaque_cut_pattern_is_not_a_background_inside_its_notch():
    host = _host()
    host["paint"]["fill"] = "#000000"
    def findings(x):
        label = {"id": "label", "kind": "Text", "purpose": "member-label", "visualRole": "text",
                 "paintOrder": 20, "bounds": {"inline": x, "block": 39, "inlineSize": 1, "blockSize": 2},
                 "paint": {"fill": "#000000", "opacity": 1}}
        scene = {"version": "chrona/scene/v0.7", "kind": "scene", "surfaces": [{"id": "test",
                 "canvasPaint": {"fill": "#FFFFFF", "opacity": 1}, "primitives": [host, label]}]}
        return [item for item in evaluate_scene_contrast(scene) if item.primitive_id == "label"]
    notch = findings(31)
    solid = findings(40)
    assert len(notch) == 1 and notch[0].ground_kind == "canvas" and notch[0].ground_id == "canvas"
    assert notch[0].contrast_ratio == 21
    assert solid and all(item.ground_id == "cut" and item.contrast_ratio == 1 for item in solid)


def test_curve_cells_reuse_existing_quadratic_flattening():
    outline = [{"kind": "move", "points": [[30, 40]]},
               {"kind": "quadratic", "points": [[60, 20], [90, 40]]},
               {"kind": "line", "points": [[90, 60]]},
               {"kind": "line", "points": [[30, 60]]},
               {"kind": "line", "points": [[30, 40]]}]
    cells = filled_trapezoids(outline)
    for y in range(22, 60, 2):
        for x in range(32, 90, 2):
            represented = any(fill_touches(_outline((*cell, cell[0])), (x, y, 0, 0)) for cell in cells)
            assert represented == fill_touches(outline, (x, y, 0, 0))


def test_candidate_copy_cap_is_not_recounted_or_bypassed_by_host_rejection():
    host = _host()
    host["pattern"]["tileInlineSize"] = host["pattern"]["tileBlockSize"] = 0.01
    host["pattern"]["primitives"] = [{"kind": "circle", "cx": 0.002, "cy": 0.002, "radius": 0.001}]
    with pytest.raises(InkTouchError, match="tile-copy limit"):
        pattern_ink_touches(host, (31, 39, 1, 1))
