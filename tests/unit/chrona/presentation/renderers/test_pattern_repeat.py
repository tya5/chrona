from dataclasses import replace
from types import SimpleNamespace

import pytest

from chrona.presentation.layout.pattern_placement import PatternTilePrimitive
from chrona.presentation.scene.model import PatternGeometry, PatternStroke, ScenePaint, ScenePrimitive
from chrona.presentation.renderers.pattern_repeat import repeat_cells


def _catalog(*, bounds=(0, 0, 24, 16), angle=0, origin=(0, 0), radius=0,
             fill=None, opacity=1):
    pattern = PatternGeometry(
        8, 8, angle, density_basis_points=1000,
        primitives=(PatternTilePrimitive("circle", cx=4, cy=4, radius=1),),
        origin=origin, region_bounds=bounds, clip_bounds=bounds,
        corner_radius=radius,
    )
    return ScenePrimitive(
        "pattern-host", "Rect", "source", "object", "role", "role", bounds,
        pattern=pattern, paint=ScenePaint(fill, "#123456", 1, (), opacity),
        corner_radius=radius,
    )


@pytest.mark.parametrize("angle", [0, 45, 90])
def test_catalog_repeat_cells_are_finite_and_cover_host(angle):
    node = _catalog(bounds=(3, 5, 29, 21), angle=angle, origin=(3, 5))
    cells = tuple(repeat_cells(node))

    assert cells
    assert all(len(cell) == 2 for cell in cells)
    assert all(abs(x) < 100 and abs(y) < 100 for x, y in cells)
    assert len(cells) < 100

    # Every host corner belongs to at least one transformed repeat tile.  Test
    # the geometric coverage rather than relying on a particular iteration
    # order or an adapter-specific serialization.
    import math
    c, s = math.cos(math.radians(angle)), math.sin(math.radians(angle))
    ox, oy = node.pattern.origin
    cx = cy = 4
    for x, y in ((3, 5), (32, 5), (3, 26), (32, 26)):
        u = cx + c * (x - ox - cx) + s * (y - oy - cy)
        v = cy - s * (x - ox - cx) + c * (y - oy - cy)
        i, j = math.floor(u / 8), math.floor(v / 8)
        # The candidate tile's transformed AABB has to be among the cells
        # returned (at exact edges either neighbor may also cover the point).
        expected = (ox + cx + c * (i * 8 - cx) - s * (j * 8 - cy),
                    oy + cy + s * (i * 8 - cx) + c * (j * 8 - cy))
        assert any(math.dist(cell, expected) < 1e-9 for cell in cells)


@pytest.mark.parametrize("angle", [0, 45, 90])
def test_catalog_repeat_cells_keep_origin_phase(angle):
    node = _catalog(bounds=(19, 9, 17, 15), angle=angle, origin=(19, 9))
    import math
    c, s = math.cos(math.radians(angle)), math.sin(math.radians(angle))
    expected = (19 + 4 - 4 * c + 4 * s, 9 + 4 - 4 * s - 4 * c)
    assert any(math.dist(cell, expected) < 1e-9 for cell in repeat_cells(node))


def test_legacy_repeat_cells_rotate_about_global_origin():
    bounds = (-12, -12, 24, 24)
    pattern = PatternGeometry(8, 8, 90, strokes=(PatternStroke((0, 0), (8, 8), 1),))
    node = ScenePrimitive("legacy", "Rect", "source", "object", "role", "role", bounds,
                          pattern=pattern,
                          paint=ScenePaint(None, "#123456", 1, (), 1))

    cells = tuple(repeat_cells(node))
    assert (0, 0) in cells
    # With legacy pivot (0, 0), the lattice remains anchored there at 90°.
    assert any(abs(x + 8) < 1e-9 and abs(y) < 1e-9 for x, y in cells)


@pytest.mark.parametrize("bad_facts", [
    {"region_bounds": (1, 0, 24, 16)},
    {"clip_bounds": (0, 0, 23, 16)},
    {"corner_radius": 2},
])
def test_catalog_mismatched_host_facts_are_rejected(bad_facts):
    node = _catalog()
    pattern = SimpleNamespace(**vars(node.pattern))
    for key, value in bad_facts.items():
        setattr(pattern, key, value)
    malformed = SimpleNamespace(kind="Rect", scene_id="bad", bounds=node.bounds,
                                pattern=pattern, paint=node.paint, corner_radius=node.corner_radius)

    with pytest.raises(ValueError, match="E_PRESENTATION_PRIMITIVE_INVALID"):
        repeat_cells(malformed)


@pytest.mark.parametrize("paint,code", [
    (ScenePaint(None, None, None, (), 1), "E_PRESENTATION_PAINT_INVALID"),
    (ScenePaint("#FFFFFF", "#123456", 1, (), 0.5), "E_PRESENTATION_PAINT_INVALID"),
])
def test_catalog_bad_pattern_paint_is_rejected(paint, code):
    node = replace(_catalog(fill="#FFFFFF"), paint=paint)
    with pytest.raises(ValueError, match=code):
        repeat_cells(node)


def test_legacy_pattern_requires_stroke_width():
    node = ScenePrimitive(
        "legacy", "Rect", "source", "object", "role", "role", (0, 0, 8, 8),
        pattern=PatternGeometry(8, 8, 0, strokes=(PatternStroke((0, 0), (8, 8), 1),)),
        paint=ScenePaint(None, "#123456", None, (), 1),
    )
    with pytest.raises(ValueError, match="E_PRESENTATION_PAINT_INVALID"):
        repeat_cells(node)
