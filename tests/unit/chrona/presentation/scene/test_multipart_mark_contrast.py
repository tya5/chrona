"""#1178: a completed multipart MARK Symbol is one figure for contrast."""
from __future__ import annotations

import pytest

from chrona.presentation.scene.contrast_policy import DEFAULT_POLICY, evaluate_scene_contrast


WHITE = "#FFFFFF"
BLACK = "#000000"
BOX = {"inline": 10, "block": 10, "inlineSize": 20, "blockSize": 10}


def _scene(*primitives, canvas=WHITE, surface="review", version="chrona/scene/v0.6"):
    return {"version": version, "kind": "scene", "surfaces": [{
        "id": surface, "canvasPaint": {"fill": canvas, "opacity": 1},
        "primitives": list(primitives), "decorationDispositions": [],
    }]}


def _mark(identifier, fill, *, role="planned", purpose="planned", source="object-1",
          order=100, bounds=None, stroke=None, opacity=1, pattern=None, surface=None):
    value = {
        "id": identifier, "kind": "Symbol", "sourceRef": source, "sourceKind": "object",
        "purpose": purpose, "visualRole": role, "paintOrder": order, "bounds": bounds or dict(BOX),
        "paint": {"fill": fill, "opacity": opacity},
    }
    if stroke is not None:
        value["paint"].update(stroke=stroke, strokeWidth=1)
    if pattern is not None:
        value["pattern"] = pattern
    return value


def _host(identifier, fill, *, order=10, opacity=1, bounds=None):
    return {
        "id": identifier, "kind": "Rect", "sourceRef": identifier, "sourceKind": "decoration",
        "purpose": "panel", "visualRole": "unclassified", "paintOrder": order,
        "bounds": bounds or dict(BOX), "paint": {"fill": fill, "opacity": opacity},
    }


def _mark_findings(findings):
    return [item for item in findings if item.visual_role == "planned"]


@pytest.mark.parametrize("suffixes", [
    (":part0", ":part1", ":part2"),
    (":part:0", ":part:1", ":part:2"),
])
def test_similarly_inked_parts_have_no_sibling_contrast_findings(suffixes):
    findings = _mark_findings(evaluate_scene_contrast(_scene(*(
        _mark(f"planned:object-1:instance-1{suffix}", BLACK, order=100 + index)
        for index, suffix in enumerate(suffixes)
    ))))

    assert not [item for item in findings if item.severity in {"warning", "error"}]


@pytest.mark.parametrize("suffixes", [
    (":part0", ":part1", ":part2"),
    (":part:0", ":part:1", ":part:2"),
])
def test_figure_is_judged_once_against_its_external_ground(suffixes):
    marks = [
        _mark(f"planned:object-1:instance-1{suffix}", BLACK, order=100 + index)
        for index, suffix in enumerate(suffixes)
    ]
    findings = _mark_findings(evaluate_scene_contrast(_scene(_host("board", BLACK), *marks)))

    assert len(findings) == 1
    finding, = findings
    assert (finding.primitive_id, finding.ground_id, finding.ground_color) == (
        f"planned:object-1:instance-1{suffixes[0]}", "board", BLACK)
    assert (finding.code, finding.severity, finding.contrast_ratio, finding.floor) == (
        "E_SCENE_MARK_CONTRAST", "error", 1.0, 3.0)


def test_best_readable_part_channel_wins_and_keeps_its_actual_identity():
    first = _mark("planned:object-1:instance-1:part:0", BLACK, order=100, stroke=WHITE)
    second = _mark("planned:object-1:instance-1:part:1", BLACK, order=101)
    findings = _mark_findings(evaluate_scene_contrast(_scene(_host("board", BLACK), first, second)))

    assert len(findings) == 1
    finding, = findings
    assert (finding.primitive_id, finding.paint_channel, finding.severity) == (
        "planned:object-1:instance-1:part:0", "stroke", "info")
    assert finding.ground_id == "board" and finding.contrast_ratio == 21.0


def test_sibling_is_excluded_during_translucent_external_ground_recursion():
    board = _host("board", BLACK, opacity=0.5)
    first = _mark("planned:object-1:instance-1:part0", WHITE, order=100)
    second = _mark("planned:object-1:instance-1:part1", BLACK, order=101)

    findings = _mark_findings(evaluate_scene_contrast(_scene(board, first, second)))

    assert len(findings) == 1
    finding, = findings
    assert (finding.primitive_id, finding.ground_id, finding.ground_kind) == (
        second["id"], "board", "translucent-over-canvas")
    assert 5.0 < finding.contrast_ratio < 6.0


def test_pattern_pair_obligations_reduce_per_part_before_figure_best_part_selection():
    pattern = {
        "tileInlineSize": 8, "tileBlockSize": 4, "angleDegrees": 45,
        "densityBasisPoints": 1250,
        "primitives": [{"kind": "rect", "x": 0, "y": 0, "inlineSize": 1, "blockSize": 4}],
        "origin": [10, 10], "regionBounds": dict(BOX), "clipBounds": dict(BOX), "cornerRadius": 0,
    }
    parts = (
        _mark("planned:object-1:instance-1:part0", WHITE, order=100, stroke=BLACK, pattern=pattern),
        _mark("planned:object-1:instance-1:part1", WHITE, order=101, stroke=BLACK, pattern=pattern),
    )

    findings = _mark_findings(evaluate_scene_contrast(
        _scene(*parts, version="chrona/scene/v0.7"),
    ))

    assert len(findings) == 1
    finding, = findings
    assert (finding.primitive_id, finding.paint_channel, finding.ground_id) == (
        parts[0]["id"], "fill", "canvas")
    assert (finding.code, finding.severity, finding.contrast_ratio, finding.density_basis_points) == (
        "E_SCENE_MARK_CONTRAST", "error", 1.0, 1250)


def test_single_part_symbol_keeps_its_existing_complete_finding_mapping():
    finding, = _mark_findings(evaluate_scene_contrast(_scene(
        _mark("planned:object-1:instance-1", BLACK),
    )))

    assert finding.as_mapping() == {
        "code": "E_SCENE_MARK_CONTRAST", "severity": "info", "scenePath": "/surfaces/0:review",
        "purpose": "planned", "visualRole": "planned", "primitiveId": "planned:object-1:instance-1",
        "contrastRatio": 21.0, "floor": 3.0, "disposition": "required", "groundId": "canvas",
        "groundColor": WHITE, "paintChannel": "fill", "sampleInline": 20.0, "sampleBlock": 15.0,
        "groundKind": "canvas", "severityClass": "legibility",
    }


def test_same_source_distinct_placements_remain_distinct_figures():
    left = {"inline": 0, "block": 0, "inlineSize": 10, "blockSize": 10}
    right = {"inline": 30, "block": 0, "inlineSize": 10, "blockSize": 10}
    marks = (
        _mark("planned:object-1:left:part0", BLACK, source="same-source", bounds=left),
        _mark("planned:object-1:left:part1", BLACK, source="same-source", order=101, bounds=left),
        _mark("planned:object-1:right:part:0", BLACK, source="same-source", bounds=right),
        _mark("planned:object-1:right:part:1", BLACK, source="same-source", order=101, bounds=right),
    )

    findings = _mark_findings(evaluate_scene_contrast(_scene(*marks)))

    assert {item.primitive_id for item in findings} == {
        "planned:object-1:left:part0", "planned:object-1:right:part:0",
    }
    assert all(item.severity == "info" for item in findings)


def test_figures_on_other_surfaces_or_with_other_roles_remain_separate():
    first = _mark("planned:object-1:instance-1:part0", BLACK)
    second = _mark("actual:object-1:instance-1:part1", BLACK, role="actual", purpose="actual", order=101)
    same_id_other_surface = _mark("planned:object-1:instance-1:part0", BLACK)
    document = _scene(first, second)
    document["surfaces"].append({
        "id": "other", "canvasPaint": {"fill": WHITE, "opacity": 1},
        "primitives": [same_id_other_surface], "decorationDispositions": [],
    })

    findings = evaluate_scene_contrast(document)

    assert {(item.scene_path, item.visual_role) for item in findings} == {
        ("/surfaces/0:review", "planned"), ("/surfaces/0:review", "actual"),
        ("/surfaces/1:other", "planned"),
    }


@pytest.mark.parametrize("failure", ["unsupported-ground", "malformed-part"])
def test_unreadable_group_fails_closed_even_when_another_part_is_readable(failure):
    host = _host("board", BLACK, opacity=2) if failure == "unsupported-ground" else _host("board", BLACK)
    valid = _mark("planned:object-1:instance-1:part:0", BLACK, order=100, stroke=WHITE)
    malformed = _mark("planned:object-1:instance-1:part:1", BLACK, order=101)
    if failure == "malformed-part":
        malformed["paint"]["fill"] = None
    findings = _mark_findings(evaluate_scene_contrast(_scene(host, valid, malformed)))

    assert len(findings) == 1
    finding, = findings
    assert finding.severity == "error"
    if failure == "unsupported-ground":
        assert (finding.code, finding.ground_id) == ("E_SCENE_CONTRAST_GROUND_UNSUPPORTED", "board")
    else:
        assert finding.code == "E_SCENE_CONTRAST_PAINT"


def test_same_source_annotation_artwork_part_remains_an_independent_layer():
    mark = _mark("planned:object-1:instance-1:part0", BLACK, source="note-1")
    artwork = {
        "id": "annotation-artwork:view-note-1:layer0:part0", "kind": "Symbol",
        "sourceRef": "note-1", "sourceKind": "annotation", "purpose": "annotation-artwork",
        "visualRole": "annotation-artwork", "paintOrder": 99, "bounds": dict(BOX),
        "paint": {"fill": BLACK, "opacity": 1},
        # A valid, non-touching outline: #848 requires readable geometry for same-source artwork.
        "symbol": {"outline": [
            {"kind": "move", "points": [[100, 100]]},
            {"kind": "line", "points": [[110, 100]]},
            {"kind": "line", "points": [[110, 110]]},
            {"kind": "line", "points": [[100, 110]]},
            {"kind": "line", "points": [[100, 100]]},
        ]},
    }

    findings = evaluate_scene_contrast(_scene(artwork, mark))

    assert {item.primitive_id for item in findings} == {mark["id"], artwork["id"]}
    mark_finding = next(item for item in findings if item.primitive_id == mark["id"])
    artwork_finding = next(item for item in findings if item.primitive_id == artwork["id"])
    assert (mark_finding.ground_id, mark_finding.severity) == ("canvas", "info")
    assert (artwork_finding.visual_role, artwork_finding.severity_class) == (
        "annotation-artwork", "decoration")


def test_legacy_body_and_band_symbols_without_part_suffix_remain_distinct_marks():
    body = _mark("body", "#5FA8FF", order=100)
    band = _mark("band", "#1B1B1B", order=101)

    findings = _mark_findings(evaluate_scene_contrast(_scene(body, band)))

    assert {item.primitive_id for item in findings} == {"body", "band"}
    assert next(item for item in findings if item.primitive_id == "band").ground_id == "body"


def test_warning_policy_emits_one_warning_for_one_failing_figure():
    parts = (
        _mark("planned:object-1:instance-1:part0", BLACK, order=100),
        _mark("planned:object-1:instance-1:part1", BLACK, order=101),
    )

    findings = _mark_findings(evaluate_scene_contrast(_scene(_host("board", BLACK), *parts), policy=DEFAULT_POLICY))

    assert len(findings) == 1
    assert (findings[0].code, findings[0].severity) == ("W_SCENE_MARK_CONTRAST", "warning")
