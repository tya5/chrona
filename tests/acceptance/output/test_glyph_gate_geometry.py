"""Literal acceptance guards for #464: the committed glyph-gates slide.

Dependency arrows must still end at the glyph's edge (issue acceptance bullet 5),
and the perceptibility gate must pass on that slide (bullet 5's second half).
"""
from pathlib import Path
import json

from chrona.presentation.scene.perceptibility import evaluate_scene_perceptibility

ROOT = Path(__file__).resolve().parents[3]
SCENE_PATH = ROOT / "examples/halcyon-1/generated/12-glyph-gates.scene.json"
TOLERANCE = 0.5


def _scene() -> dict:
    return json.loads(SCENE_PATH.read_text(encoding="utf-8"))


def _glyph_gate_symbols(primitives: list[dict]) -> dict[str, list[dict]]:
    """Group a glyph gate's sibling Symbol part-primitives by their shared mark."""
    groups: dict[str, list[dict]] = {}
    for item in primitives:
        if item["kind"] != "Symbol" or ":part" not in item["id"]:
            continue
        mark_id = item["id"].rsplit(":part", 1)[0]
        groups.setdefault(mark_id, []).append(item)
    return groups


def test_glyph_gate_parts_reach_the_mark_bounds_left_and_right_edge_at_the_centre_line():
    surface = _scene()["surfaces"][0]
    groups = _glyph_gate_symbols(surface["primitives"])
    assert groups, "the committed slide has no multi-part glyph gates to check"
    for mark_id, parts in groups.items():
        bounds = parts[0]["bounds"]
        centre = bounds["block"] + bounds["blockSize"] / 2
        left_edge, right_edge = bounds["inline"], bounds["inline"] + bounds["inlineSize"]
        xs_at_centre: list[float] = []
        for part in parts:
            for command in part["symbol"]["outline"]:
                for point in command["points"]:
                    if abs(point[1] - centre) <= TOLERANCE:
                        xs_at_centre.append(point[0])
        assert xs_at_centre, f"{mark_id} has no glyph outline point on its own centre line"
        assert abs(min(xs_at_centre) - left_edge) <= TOLERANCE, mark_id
        assert abs(max(xs_at_centre) - right_edge) <= TOLERANCE, mark_id


def test_every_dependency_route_terminal_touching_a_glyph_gate_lies_on_its_box_edge():
    surface = _scene()["surfaces"][0]
    groups = _glyph_gate_symbols(surface["primitives"])
    bounds_by_object = {mark_id.split(":")[1]: parts[0]["bounds"] for mark_id, parts in groups.items()}
    routes = [item for item in surface["primitives"] if item["kind"] == "Path" and item["purpose"] == "dependency"]
    assert routes
    checked = 0
    for route in routes:
        source_ref = route["sourceRef"]
        for object_id, bounds in bounds_by_object.items():
            if object_id not in source_ref:
                continue
            left_edge, right_edge = bounds["inline"], bounds["inline"] + bounds["inlineSize"]
            top_edge, bottom_edge = bounds["block"], bounds["block"] + bounds["blockSize"]
            for point in (route["points"][0], route["points"][-1]):
                on_vertical_edge = (abs(point[0] - left_edge) <= TOLERANCE or abs(point[0] - right_edge) <= TOLERANCE)
                on_horizontal_edge = (abs(point[1] - top_edge) <= TOLERANCE or abs(point[1] - bottom_edge) <= TOLERANCE)
                inside_inline = left_edge - TOLERANCE <= point[0] <= right_edge + TOLERANCE
                inside_block = top_edge - TOLERANCE <= point[1] <= bottom_edge + TOLERANCE
                if inside_inline and inside_block and (on_vertical_edge or on_horizontal_edge):
                    checked += 1
    assert checked > 0, "no dependency route terminal was found on a glyph gate's box edge"


def test_glyph_gates_slide_passes_the_perceptibility_gate():
    findings = evaluate_scene_perceptibility(_scene())
    errors = [finding for finding in findings if finding.severity == "error"]
    assert not errors, errors
