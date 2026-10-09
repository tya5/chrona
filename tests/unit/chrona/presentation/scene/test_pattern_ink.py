import json
import math
from dataclasses import replace

import pytest

from chrona.presentation.layout.model import Rect
from chrona.presentation.layout.pattern_placement import complete_pattern_placement
from chrona.presentation.scene.ink_touch import InkTouchError
from chrona.presentation.scene.model import (
    ContentFamilyCounts,
    InspectionScene,
    SceneManifest,
    ScenePaint,
    ScenePrimitive,
    SceneProvenance,
    SceneSlot,
    SceneSurface,
)
from chrona.presentation.scene.pattern_geometry import project_pattern_placement
from chrona.presentation.scene.pattern_ink import pattern_ink_touches
from chrona.presentation.scene.serialization import serialize_scene


def _primitive(*, tile=(10, 10), angle=0, origin=(0, 0), region=(0, 0, 100, 100), primitives=None):
    return {
        "kind": "Rect", "bounds": region,
        "paint": {"fill": None, "stroke": "#202020", "opacity": 1},
        "pattern": {
            "tileInlineSize": tile[0], "tileBlockSize": tile[1], "angleDegrees": angle,
            "origin": origin, "regionBounds": region, "clipBounds": region,
            "primitives": primitives or [{"kind": "circle", "cx": 2, "cy": 2, "radius": 1}],
        },
    }


def test_circle_contact_repeats_and_noncontact_in_same_tile_is_false():
    scene_primitive = _primitive()
    assert pattern_ink_touches(scene_primitive, (1.5, 1.5, 0.2, 0.2))
    assert not pattern_ink_touches(scene_primitive, (4, 4, 1, 1))
    assert pattern_ink_touches(scene_primitive, (12, 2, 0.2, 0.2))


def test_circle_stroke_contact_uses_closed_annulus_and_preserves_its_hole():
    primitive = _primitive(primitives=[{
        "kind": "circle", "cx": 5, "cy": 5, "radius": 2,
        "fillChannel": "none", "strokeWidth": 0.2,
    }])
    assert not pattern_ink_touches(primitive, (4.95, 4.95, 0.1, 0.1))
    assert pattern_ink_touches(primitive, (7.09, 4.95, 0.1, 0.1))
    assert not pattern_ink_touches(primitive, (7.11, 4.95, 0.1, 0.1))
    # A query exactly tangent to the outer annulus boundary is included.
    assert pattern_ink_touches(primitive, (7.1, 5.0, 0, 0))


def test_filled_and_substrate_circle_operations_have_distinct_sparse_contact_policy():
    filled = _primitive(primitives=[{
        "kind": "circle", "cx": 5, "cy": 5, "radius": 2, "strokeWidth": 0.2,
    }])
    assert pattern_ink_touches(filled, (4.95, 4.95, 0.1, 0.1))
    substrate = _primitive(primitives=[{
        "kind": "circle", "cx": 5, "cy": 5, "radius": 2,
        "fillChannel": "substrate", "strokeWidth": 0.2,
    }])
    with pytest.raises(InkTouchError, match="substrate circle reached sparse-ink observer"):
        pattern_ink_touches(substrate, (7, 5, 0, 0))
    unpainted = _primitive(primitives=[{
        "kind": "circle", "cx": 5, "cy": 5, "radius": 2, "fillChannel": "none",
    }])
    with pytest.raises(InkTouchError, match="unpainted pattern circle"):
        pattern_ink_touches(unpainted, (7, 5, 0, 0))


def test_stroked_circle_contact_uses_inverse_rotation_and_closed_tile_seam():
    scene_primitive = _primitive(
        tile=(10, 10), angle=90, origin=(12, 14), region=(12, 14, 30, 30),
        primitives=[{"kind": "circle", "cx": 2, "cy": 3, "radius": 1,
                     "fillChannel": "none", "strokeWidth": 0.2}],
    )
    # The transformed center is (19, 16); a 90-degree rotation preserves the annulus.
    assert pattern_ink_touches(scene_primitive, (20.08, 15.99, 0.04, 0.02))
    assert not pattern_ink_touches(scene_primitive, (18.99, 15.99, 0.02, 0.02))
    # Circle paint is clipped at the tile boundary before repetition; a protruding
    # stroke from the first copy cannot leak into the neighboring tile.
    seam = _primitive(tile=(10, 10), primitives=[{
        "kind": "circle", "cx": 9.5, "cy": 5, "radius": 0.2,
        "fillChannel": "none", "strokeWidth": 0.4,
    }])
    assert pattern_ink_touches(seam, (9.89, 4.99, 0.05, 0.02))
    assert not pattern_ink_touches(seam, (10.11, 4.99, 0.05, 0.02))


def test_extreme_circle_radial_arithmetic_fails_closed():
    scene_primitive = _primitive(tile=(1e308, 10), origin=(1e308, 0),
                                 region=(1e308, 0, 2e292, 1),
                                 primitives=[{
        "kind": "circle", "cx": -1.797e308, "cy": 5, "radius": 1,
        "fillChannel": "none", "strokeWidth": 1,
    }])
    with pytest.raises(InkTouchError, match="non-finite pattern circle radial range"):
        pattern_ink_touches(scene_primitive, (1e308, 0, 2e292, 1))


def test_filled_tile_rect_uses_its_actual_ink_footprint():
    scene_primitive = _primitive(primitives=[
        {"kind": "rect", "x": 3, "y": 4, "inlineSize": 2, "blockSize": 1},
    ])
    assert pattern_ink_touches(scene_primitive, (4.9, 4.5, 0.2, 0.2))
    assert not pattern_ink_touches(scene_primitive, (6, 4, 1, 1))


def test_rotated_nonzero_origin_maps_world_bounds_back_to_tile_ink():
    scene_primitive = _primitive(
        angle=90, origin=(12, 14), region=(12, 14, 60, 60),
        primitives=[{"kind": "circle", "cx": 2, "cy": 3, "radius": 0.75}],
    )
    # Forward: origin + centre + R((2,3) - centre) == (19,16).
    assert pattern_ink_touches(scene_primitive, (18.5, 15.5, 1, 1))
    assert not pattern_ink_touches(scene_primitive, (26, 20, 1, 1))


def test_tile_seam_is_closed_and_pattern_clip_is_respected():
    scene_primitive = _primitive(primitives=[{"kind": "circle", "cx": 9.5, "cy": 5, "radius": 0.5}])
    assert pattern_ink_touches(scene_primitive, (9.9, 4.9, 0.1, 0.2))
    assert not pattern_ink_touches(scene_primitive, (100.01, 5, 1, 1))


def test_primitives_are_clipped_to_each_tile_before_contact():
    protruding = _primitive(primitives=[
        {"kind": "rect", "x": 9.5, "y": 2, "inlineSize": 2, "blockSize": 2},
    ])
    # The first copy protrudes past x=10, but the next tile copy begins at x=19.5.
    assert not pattern_ink_touches(protruding, (10.1, 2.5, 0.2, 0.2))


def test_filled_path_hole_remains_empty_while_ring_contacts():
    ring = {"kind": "path", "paint": "fill", "commands": [
        {"kind": "move", "points": [1, 1]}, {"kind": "line", "points": [9, 1]},
        {"kind": "line", "points": [9, 9]}, {"kind": "line", "points": [1, 9]},
        {"kind": "close", "points": []},
        {"kind": "move", "points": [3, 3]}, {"kind": "line", "points": [3, 7]},
        {"kind": "line", "points": [7, 7]}, {"kind": "line", "points": [7, 3]},
        {"kind": "close", "points": []},
    ]}
    scene_primitive = _primitive(primitives=[ring])
    assert not pattern_ink_touches(scene_primitive, (4, 4, 1, 1))
    assert pattern_ink_touches(scene_primitive, (2, 4, 0.5, 1))


def test_stroked_path_uses_completed_width_and_rejects_invalid_geometry():
    line = {"kind": "path", "paint": "stroke", "strokeWidth": 2,
            "lineCap": "butt", "lineJoin": "miter", "commands": [
                {"kind": "move", "points": [1, 5]}, {"kind": "line", "points": [9, 5]}]}
    scene_primitive = _primitive(primitives=[line])
    assert pattern_ink_touches(scene_primitive, (4, 5.8, 1, 0.1))
    assert not pattern_ink_touches(scene_primitive, (4, 6.1, 1, 0.1))
    scene_primitive["pattern"]["primitives"] = [{"kind": "mystery"}]
    with pytest.raises(InkTouchError):
        pattern_ink_touches(scene_primitive, (4, 5, 1, 1))


def test_extreme_finite_stroke_endpoints_fail_closed_on_nonfinite_segment_math():
    stroke = _primitive(tile=(10, 10), region=(0, 0, 10, 10), primitives=[{
        "kind": "path", "paint": "stroke", "strokeWidth": 1,
        "lineCap": "butt", "lineJoin": "miter", "commands": [
            {"kind": "move", "points": [-1e308, 5]},
            {"kind": "line", "points": [1e308, 5]},
        ],
    }])
    with pytest.raises(InkTouchError, match="non-finite pattern stroke segment"):
        pattern_ink_touches(stroke, (4, 4.9, 1, 0.2))


@pytest.mark.parametrize(("cap", "expected"), [("butt", False), ("round", False), ("square", True)])
def test_open_path_cap_geometry_is_respected(cap, expected):
    line = {"kind": "path", "paint": "stroke", "strokeWidth": 2,
            "lineCap": cap, "lineJoin": "miter", "commands": [
                {"kind": "move", "points": [20, 50]}, {"kind": "line", "points": [50, 50]}]}
    scene_primitive = _primitive(tile=(100, 100), primitives=[line])
    assert pattern_ink_touches(scene_primitive, (50.9, 50.9, 0.1, 0.1)) is expected


def test_miter_join_reaches_its_offset_intersection_beyond_bevel_and_round_joins():
    def joined(join):
        return _primitive(tile=(100, 100), primitives=[{
            "kind": "path", "paint": "stroke", "strokeWidth": 2,
            "lineCap": "butt", "lineJoin": join, "commands": [
                {"kind": "move", "points": [20, 50]}, {"kind": "line", "points": [50, 50]},
                {"kind": "line", "points": [80, 67.3205080757]},
            ],
        }])
    # For this 30-degree turn the offset-line miter is about (50.268, 49),
    # whereas bevel/round do not reach this small box above their join body.
    sample = (50.26, 48.99, 0.02, 0.02)
    assert pattern_ink_touches(joined("miter"), sample)
    assert not pattern_ink_touches(joined("bevel"), sample)
    assert not pattern_ink_touches(joined("round"), sample)


def test_overlimit_miter_uses_the_published_bounded_local_disk():
    sharp = _primitive(tile=(100, 100), primitives=[{
        "kind": "path", "paint": "stroke", "strokeWidth": 2,
        "lineCap": "butt", "lineJoin": "miter", "commands": [
            {"kind": "move", "points": [20, 50]}, {"kind": "line", "points": [50, 50]},
            {"kind": "line", "points": [20.114, 52.615]},
        ],
    }])
    # The near-reversal's offset intersection exceeds 10 stroke widths; the
    # declared conservative disk remains local to this join, not the tile.
    assert pattern_ink_touches(sharp, (69.5, 49.9, 0.1, 0.1))
    assert not pattern_ink_touches(sharp, (80, 80, 0.1, 0.1))


def test_tiny_nonzero_reversal_uses_bounded_miter_envelope():
    sharp = _primitive(tile=(100, 100), primitives=[{
        "kind": "path", "paint": "stroke", "strokeWidth": 2,
        "lineCap": "butt", "lineJoin": "miter", "commands": [
            {"kind": "move", "points": [20, 50]}, {"kind": "line", "points": [50, 50]},
            {"kind": "line", "points": [20, 50.00000000000001]},
        ],
    }])
    # The nonzero turn cross product is below 1e-12. It still has a finite
    # offset intersection beyond the admitted miter reach, so the published
    # local conservative disk applies instead of silently skipping the join.
    assert pattern_ink_touches(sharp, (50, 69.5, 0.1, 0.1))


def test_move_only_stroked_path_fails_closed_without_indexing_adjacent_point():
    move_only = _primitive(tile=(100, 100), primitives=[{
        "kind": "path", "paint": "stroke", "strokeWidth": 2,
        "lineCap": "square", "lineJoin": "miter", "commands": [
            {"kind": "move", "points": [50, 50]},
        ],
    }])
    with pytest.raises(InkTouchError, match="empty pattern path"):
        pattern_ink_touches(move_only, (49, 49, 2, 2))


def test_candidate_tile_copy_bound_allows_4096_and_rejects_4097_before_ink_test():
    scene_primitive = _primitive(tile=(1, 1), region=(0, 0, 5000, 1),
                                 primitives=[{"kind": "circle", "cx": 0.75, "cy": 0.75, "radius": 0.1}])
    assert not pattern_ink_touches(scene_primitive, (0.25, 0.25, 4095, 0))
    with pytest.raises(InkTouchError, match="candidate tile-copy limit"):
        pattern_ink_touches(scene_primitive, (0.25, 0.25, 4096, 0))


def test_unreadable_paint_and_nonfinite_subject_fail_closed():
    scene_primitive = _primitive()
    scene_primitive["paint"]["stroke"] = None
    with pytest.raises(InkTouchError):
        pattern_ink_touches(scene_primitive, (1, 1, 1, 1))
    scene_primitive["paint"]["stroke"] = "#202020"
    with pytest.raises(InkTouchError):
        pattern_ink_touches(scene_primitive, (0, 0, math.inf, 1))


def test_explicit_null_circle_operation_field_fails_closed():
    scene_primitive = _primitive(primitives=[{
        "kind": "circle", "cx": 2, "cy": 2, "radius": 1, "strokeWidth": None,
    }])
    with pytest.raises(InkTouchError, match="invalid pattern circle stroke width"):
        pattern_ink_touches(scene_primitive, (1, 1, 2, 2))


def test_serialized_scene_mapping_uses_public_bounds_and_projected_pattern_shapes():
    bounds = Rect(12, 14, 60, 60)
    completed = complete_pattern_placement({
        "kind": "catalog", "tile": {"inlineSize": 10, "blockSize": 10}, "angle": 90,
        "densityBasisPoints": 1000,
        "primitives": [{"kind": "circle", "cx": 2, "cy": 3, "radius": 0.75}],
    }, bounds)
    slot = SceneSlot("slot", "source", None, (12, 14, 60, 60))
    scene_primitive = ScenePrimitive(
        "patterned", "Rect", "source", "test", "decoration", "test",
        (12, 14, 60, 60), slot_id="slot", pattern=project_pattern_placement(completed),
        paint=ScenePaint(None, "#202020", None, (), 1),
    )
    surface = SceneSurface("surface", (slot,), (), (), None, (scene_primitive,), canvas_bounds=(12, 14, 60, 60))
    manifest = SceneManifest("chrona/scene-manifest/v0.1", "test", (60, 60), (), (),
                             ContentFamilyCounts(0, 0, 0, 0, 0), ())
    scene = InspectionScene(SceneProvenance("draft", "test", ()), (60, 60), (), (surface,), manifest, ())
    document = json.loads(serialize_scene(scene))
    mapping = document["surfaces"][0]["primitives"][0]
    assert isinstance(mapping["bounds"], dict)
    assert mapping["pattern"]["primitives"] == [{"kind": "circle", "cx": 2.0, "cy": 3.0, "radius": 0.75}]
    assert pattern_ink_touches(mapping, (18.5, 15.5, 1, 1))


def test_nondefault_circle_operations_are_serialized_but_default_fields_are_omitted():
    bounds = Rect(0, 0, 20, 20)
    completed = complete_pattern_placement({
        "tile": {"inlineSize": 10, "blockSize": 10}, "angle": 0,
        "densityBasisPoints": 5000,
        "primitives": [
            {"kind": "circle", "cx": 2, "cy": 2, "radius": 1},
            {"kind": "circle", "cx": 5, "cy": 5, "radius": 2,
             "fillChannel": "substrate", "strokeWidth": 0.5},
        ],
    }, bounds)
    pattern = project_pattern_placement(completed)
    slot = SceneSlot("slot", "source", None, (0, 0, 20, 20))
    patterned = ScenePrimitive("patterned", "Rect", "source", "test", "decoration", "test",
                               (0, 0, 20, 20), slot_id="slot", pattern=pattern,
                               paint=ScenePaint("#FFFFFF", "#202020", None, (), 1))
    surface = SceneSurface("surface", (slot,), (), (), None, (patterned,), canvas_bounds=(0, 0, 20, 20))
    manifest = SceneManifest("chrona/scene-manifest/v0.1", "test", (20, 20), (), (),
                             ContentFamilyCounts(0, 0, 0, 0, 0), ())
    scene = InspectionScene(SceneProvenance("draft", "test", ()), (20, 20), (), (surface,), manifest, ())
    primitives = json.loads(serialize_scene(scene))["surfaces"][0]["primitives"][0]["pattern"]["primitives"]
    assert primitives == [
        {"kind": "circle", "cx": 2.0, "cy": 2.0, "radius": 1.0},
        {"kind": "circle", "cx": 5.0, "cy": 5.0, "radius": 2.0,
         "fillChannel": "substrate", "strokeWidth": 0.5},
    ]
