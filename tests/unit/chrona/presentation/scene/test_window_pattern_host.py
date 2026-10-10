"""The same completed pattern-host contract guards typed and public Scenes."""
from dataclasses import replace
import json

import pytest

from chrona.presentation.layout.surface_quality import PaintClip, PathCommand
from chrona.presentation.layout.pattern_placement import PatternTilePrimitive
from chrona.presentation.scene.model import (
    ContentFamilyCounts, InspectionScene, PatternGeometry, PatternStroke,
    SceneManifest, ScenePrimitive, SceneProvenance, SceneSlot, SceneSurface, SymbolGeometry,
)
from chrona.presentation.scene.serialization import (
    SceneSerializationError, scene_document, serialize_scene, validate_scene_document,
)


BOUNDS = (10, 20, 30, 12)
OUTLINE = tuple(PathCommand(kind, points) for kind, points in (
    ("move", ((10, 20),)), ("line", ((40, 20),)), ("line", ((40, 32),)),
    ("line", ((10, 32),)), ("line", ((13, 26),)), ("line", ((10, 20),)),
))


def _pattern(**changes):
    return PatternGeometry(8, 8, 0, density_basis_points=1250,
                           primitives=(PatternTilePrimitive("circle", cx=2, cy=2, radius=1),),
                           **({"origin": (-30, 20), "region_bounds": BOUNDS,
                               "clip_bounds": BOUNDS, "corner_radius": 0} | changes))


def _host(**changes):
    return ScenePrimitive(**({"scene_id": "cut", "kind": "Symbol", "source_ref": "source",
                              "source_kind": "object", "purpose": "progress-fill",
                              "visual_role": "progress-fill", "bounds": BOUNDS,
                              "slot_id": "timeline", "symbol": SymbolGeometry(OUTLINE),
                              "pattern": _pattern(), "paint_clip": PaintClip((10, 0, 60, 100))} | changes))


def _scene(host):
    slot = SceneSlot("timeline", "timeline", None, (0, 0, 100, 100))
    surface = SceneSurface("timeline", (slot,), (), (), None, (host,), canvas_bounds=(0, 0, 100, 100))
    manifest = SceneManifest("chrona/scene-manifest/v0.1", "test", (100, 100), (), (),
                             ContentFamilyCounts(0, 0, 0, 0, 0), ())
    return InspectionScene(SceneProvenance("draft", "test", ()), (100, 100), (), (surface,), manifest, ())


@pytest.mark.parametrize("purpose,role", [("progress-fill", "progress-fill"),
                                          ("summary-bar", "summary-bar"),
                                          ("missingActual", "missing-actual")])
def test_cut_host_keeps_original_phase_and_own_contour_in_public_scene(purpose, role):
    scene = _scene(_host(purpose=purpose, visual_role=role))
    document = scene_document(scene)
    validate_scene_document(document)
    host = document["surfaces"][0]["primitives"][0]
    assert document["version"] == "chrona/scene/v0.7"
    assert host["pattern"]["origin"] == [-30, 20]
    assert host["pattern"]["regionBounds"] == host["bounds"] == host["pattern"]["clipBounds"]
    assert len(host["symbol"]["outline"]) == len(OUTLINE)
    assert "cutContour" not in host["pattern"]
    assert json.loads(serialize_scene(scene)) == document


@pytest.mark.parametrize("changes", [
    {"paint_clip": None}, {"purpose": "planned", "visual_role": "planned"},
    {"purpose": "summary-bar"}, {"end_treatment": "open"},
    {"symbol": SymbolGeometry(OUTLINE[:-1])},
    {"symbol": SymbolGeometry((PathCommand("line", ((10, 20),)),))},
    {"symbol": SymbolGeometry((PathCommand("move", ((10, 20),)),))},
    {"symbol": SymbolGeometry(OUTLINE + (PathCommand("move", ((15, 25),)),
                                           PathCommand("line", ((16, 25),))))},
    {"pattern": _pattern(clip_bounds=(10, 20, 20, 12))},
    {"pattern": _pattern(corner_radius=2)},
    {"pattern": _pattern(origin=(float("nan"), 20))},
    {"glyph_paint_mode": "fill"},
    {"pattern": PatternGeometry(8, 8, 0, (PatternStroke((0, 0), (0, 8), 1),))},
])
def test_typed_scene_rejects_incomplete_or_arbitrary_pattern_symbol(changes):
    with pytest.raises(ValueError, match="E_PRESENTATION_PRIMITIVE_INVALID"):
        _host(**changes)


@pytest.mark.parametrize("mutation", ["clip", "outline", "role", "region", "radius", "rect-phase"])
def test_raw_document_cannot_bypass_completed_pattern_host_contract(mutation):
    document = scene_document(_scene(_host()))
    host = document["surfaces"][0]["primitives"][0]
    if mutation == "clip":
        del host["paintClip"]
    elif mutation == "outline":
        host["symbol"]["outline"].pop()
    elif mutation == "role":
        host["purpose"] = host["visualRole"] = "icon-mark"
    elif mutation == "region":
        host["pattern"]["regionBounds"]["inlineSize"] = 29
    elif mutation == "radius":
        host["pattern"]["cornerRadius"] = 1
    else:
        host["kind"] = "Rect"
        del host["symbol"]
    with pytest.raises(SceneSerializationError, match="E_PRESENTATION_PRIMITIVE_INVALID"):
        validate_scene_document(document)


def test_ordinary_rect_still_requires_original_region_phase():
    rect = _host(kind="Rect", symbol=None, paint_clip=None,
                 pattern=_pattern(origin=(10, 20), corner_radius=2))
    assert serialize_scene(_scene(rect))
    with pytest.raises(ValueError, match="E_PRESENTATION_PRIMITIVE_INVALID"):
        replace(rect, pattern=_pattern())


def test_v06_does_not_admit_catalog_window_symbol():
    document = scene_document(_scene(_host()))
    document["version"] = "chrona/scene/v0.6"
    with pytest.raises(SceneSerializationError):
        validate_scene_document(document)


def test_multiple_closed_subpaths_retain_hole_contour():
    hole = tuple(PathCommand(kind, points) for kind, points in (
        ("move", ((20, 22),)), ("line", ((20, 25),)), ("line", ((23, 25),)),
        ("line", ((23, 22),)), ("line", ((20, 22),))))
    assert serialize_scene(_scene(_host(symbol=SymbolGeometry(OUTLINE + hole))))
