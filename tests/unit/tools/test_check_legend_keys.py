"""Synthetic controls for corpus legend/mark Scene checks (#1396)."""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path

import pytest

from tools import check_legend_keys as checker
from tools.check_legend_keys import legend_key_findings


def _rect(identifier: str, *, fill: str | None = "#B06020", kind: str = "Rect",
          bounds: dict | None = None, stroke: str | None = None,
          source_ref: str | None = None) -> dict:
    result = {"id": identifier, "kind": kind,
            "paint": {"fill": fill, "stroke": stroke},
            "bounds": bounds or {"inline": 0, "block": 0, "inlineSize": 10, "blockSize": 4}}
    if source_ref is not None:
        result["sourceRef"] = source_ref
    return result


def _scene(*surfaces: list[dict]) -> dict:
    return {"surfaces": [{"primitives": primitives} for primitives in surfaces]}


@pytest.mark.parametrize("role", ["planned", "actual", "snapshot", "scenario"])
def test_bar_key_family_and_paint_match(role):
    suffix = ":ink-a" if role == "actual" else ""
    scene = _scene([_rect(f"{role}:host"), _rect(f"legend-swatch:{role}{suffix}")])
    assert legend_key_findings(scene) == []


@pytest.mark.parametrize("role", ["planned", "snapshot", "scenario"])
@pytest.mark.parametrize("wrong_kind", ["Symbol", "Path"])
def test_bar_key_rejects_wrong_shape_family(role, wrong_kind):
    scene = _scene([_rect(f"{role}:host"), _rect(f"legend-swatch:{role}", kind=wrong_kind)])
    assert any(role in finding and "shape" in finding.lower() for finding in legend_key_findings(scene))


@pytest.mark.parametrize("role", ["planned", "actual", "snapshot", "scenario"])
def test_bar_key_rejects_wrong_paint(role):
    suffix = ":ink-a" if role == "actual" else ""
    scene = _scene([_rect(f"{role}:host"), _rect(f"legend-swatch:{role}{suffix}", fill=None)])
    assert any(role in finding and "paint" in finding.lower() for finding in legend_key_findings(scene))


def test_milestone_key_matches_the_planned_point_shape_and_paint():
    scene = _scene([_rect("planned:gate", kind="Symbol", fill=None),
                    _rect("legend-swatch:milestone", kind="Symbol", fill=None)])
    assert legend_key_findings(scene) == []

    broken = deepcopy(scene)
    broken["surfaces"][0]["primitives"][1]["kind"] = "Rect"
    findings = legend_key_findings(broken)
    assert any("milestone" in finding and "shape" in finding.lower() for finding in findings)

    broken = deepcopy(scene)
    broken["surfaces"][0]["primitives"][1]["paint"]["fill"] = "#000000"
    findings = legend_key_findings(broken)
    assert any("milestone" in finding and "paint" in finding.lower() for finding in findings)


def _gate_scene(*, key_fill: str | None, mark_fill: str | None, ghost: bool) -> dict:
    primitives = [_rect("planned:m0-gate:m0-gate:part0", kind="Symbol", fill=mark_fill),
                  _rect("legend-swatch:milestone:part0", kind="Symbol", fill=key_fill)]
    if ghost:  # ghost-when-changed draws the baseline gate stroke-only, first in order
        ghost_item = _rect("planned:m0-gate:snapshot:m0-gate:part0", kind="Symbol", fill=None)
        ghost_item["paint"]["stroke"] = "#808080"
        primitives.insert(0, ghost_item)
    return _scene(primitives)


def test_milestone_key_ignores_baseline_gate_ghosts():
    assert legend_key_findings(_gate_scene(key_fill="#B06020", mark_fill="#B06020", ghost=True)) == []


def test_milestone_key_with_ghosts_still_rejects_a_real_mismatch():
    scene = _gate_scene(key_fill="#B06020", mark_fill=None, ghost=True)
    scene["surfaces"][0]["primitives"][1]["paint"]["stroke"] = "#000000"
    findings = legend_key_findings(scene)
    assert any("milestone" in finding and "paint" in finding.lower() for finding in findings)


def test_multipart_milestone_key_matches_the_complete_source_figure_palette():
    bounds = {"inline": 0, "block": 0, "inlineSize": 10, "blockSize": 10}
    scene = _scene([
        _rect("planned:gate:part0", kind="Symbol", fill="#5FA8FF", bounds=bounds,
              source_ref="gate"),
        _rect("planned:gate:part1", kind="Symbol", fill="#1B1B1B", bounds=bounds,
              source_ref="gate", stroke="#EAF0FA"),
        _rect("legend-swatch:milestone:part0", kind="Symbol", fill="#5FA8FF", bounds=bounds,
              source_ref="milestone"),
        _rect("legend-swatch:milestone:part1", kind="Symbol", fill="#1B1B1B", bounds=bounds,
              source_ref="milestone", stroke="#EAF0FA"),
    ])
    assert legend_key_findings(scene) == []

    broken = deepcopy(scene)
    broken["surfaces"][0]["primitives"][2]["paint"]["fill"] = "#000000"
    assert any("milestone" in item and "fill/stroke" in item for item in legend_key_findings(broken))

    broken = deepcopy(scene)
    broken["surfaces"][0]["primitives"][-1]["paint"]["stroke"] = "#FFFFFF"
    assert any("milestone" in item and "fill/stroke" in item for item in legend_key_findings(broken))

    broken = deepcopy(scene)
    broken["surfaces"][0]["primitives"].pop(-1)
    assert any("milestone" in item and "fill/stroke" in item for item in legend_key_findings(broken))

    broken = deepcopy(scene)
    first = broken["surfaces"][0]["primitives"][2]["paint"]["fill"]
    broken["surfaces"][0]["primitives"][2]["paint"]["fill"] = "#1B1B1B"
    broken["surfaces"][0]["primitives"][3]["paint"]["fill"] = first
    assert any("milestone" in item and "fill/stroke" in item for item in legend_key_findings(broken))


def test_state_point_key_is_not_misclassified_by_its_owner_role():
    mark = _rect("planned:gate", kind="Symbol", fill="#B06020", source_ref="gate")
    mark["visualRole"] = "planned"
    key = _rect("legend-swatch:planned:opaque-digest", kind="Symbol", fill="#B06020",
                source_ref="planned:opaque-digest")
    key.update(sourceKind="legend", visualRole="planned")
    # A planned bar and its ordinary key may coexist with a planned point key.
    scene = _scene([_rect("planned:bar"), _rect("legend-swatch:planned"), mark, key])
    assert legend_key_findings(scene) == []

    broken = deepcopy(scene)
    broken["surfaces"][0]["primitives"][-1]["paint"]["fill"] = "#000000"
    assert any("planned" in finding and "point figure" in finding
               for finding in legend_key_findings(broken))

    orphan = _rect("legend-swatch:actual:opaque-digest", kind="Symbol", fill="#B06020",
                   source_ref="actual:opaque-digest")
    orphan.update(sourceKind="legend", visualRole="actual")
    assert any("no source Symbol" in finding for finding in legend_key_findings(_scene([orphan])))


def test_each_point_key_matches_one_complete_multipart_source_figure():
    bounds = {"inline": 0, "block": 0, "inlineSize": 10, "blockSize": 10}

    def part(identifier, source, fill, stroke=None):
        item = _rect(identifier, kind="Symbol", fill=fill, stroke=stroke,
                     bounds=bounds, source_ref=source)
        item["visualRole"] = "planned"
        if identifier.startswith("legend-swatch:"):
            item["sourceKind"] = "legend"
        return item

    scene = _scene([
        part("planned:gate-a:part0", "gate-a", "#AA0000"),
        part("planned:gate-a:part1", "gate-a", "#111111", "#EEEEEE"),
        part("planned:gate-b:part0", "gate-b", "#0000AA"),
        part("planned:gate-b:part1", "gate-b", "#FFFFFF", "#222222"),
        part("legend-swatch:milestone:part0", "key-a", "#AA0000"),
        part("legend-swatch:milestone:part1", "key-a", "#111111", "#EEEEEE"),
    ])
    # The key's declared owner is milestone, while semanticId carries point state.
    assert legend_key_findings(scene) == []

    # A hybrid assembled from individually valid parts is not a source figure.
    broken = deepcopy(scene)
    broken["surfaces"][0]["primitives"][-1]["paint"] = {
        "fill": "#FFFFFF", "stroke": "#222222"}
    assert any("complete figure" in finding for finding in legend_key_findings(broken))


@pytest.mark.parametrize("visual_role", ["gate", "custom-milestone"])
def test_milestone_point_key_matches_its_completed_visual_role(visual_role):
    bounds = {"inline": 12, "block": 20, "inlineSize": 10, "blockSize": 10}

    def part(identifier, source, fill, stroke=None, *, legend=False):
        item = _rect(identifier, kind="Symbol", fill=fill, stroke=stroke,
                     bounds=bounds, source_ref=source)
        item.update(purpose="planned" if not legend else "legend-swatch",
                    visualRole=visual_role)
        if legend:
            item["sourceKind"] = "legend"
        else:
            item["sourceKind"] = "object"
        return item

    scene = _scene([
        part("planned:milestone-a:part0", "milestone-a", "#B06020"),
        part("planned:milestone-a:part1", "milestone-a", None, "#102030"),
        part("legend-swatch:milestone:opaque-id:part0", "key", "#B06020", legend=True),
        part("legend-swatch:milestone:opaque-id:part1", "key", None, "#102030", legend=True),
    ])
    assert legend_key_findings(scene) == []

    broken = deepcopy(scene)
    broken["surfaces"][0]["primitives"][-1]["paint"]["stroke"] = "#FFFFFF"
    assert any("complete figure" in finding for finding in legend_key_findings(broken))


def _fill_witness(value="open", *, scale_id="status-scale", field="status", source_id="view-a"):
    return {"channel": "fill", "scaleId": scale_id, "field": field, "value": value,
            "sources": [{"kind": "view", "id": source_id, "sourceRef": "/body/colorEncoding"}]}


def _neutral_encoded_point_scene(witnesses=None, *, scale_fill="#AA0000", key_fill="#333333",
                                 key_gradient=None, key_stroke="#111111"):
    witnesses = witnesses or [_fill_witness()]
    bounds = {"inline": 10, "block": 20, "inlineSize": 10, "blockSize": 10}
    primitives = []
    for index, witness in enumerate(witnesses):
        fill = scale_fill
        mark = _rect(f"planned:opaque-object-{index}", kind="Symbol", fill=fill,
                     bounds=bounds, source_ref=f"object-{index}", stroke="#111111")
        mark.update(sourceKind="object", purpose="planned", visualRole="planned", encoding=witness)
        primitives.append(mark)

    state_paint = {"fill": key_fill, "stroke": key_stroke}
    if key_gradient is not None:
        state_paint["gradient"] = key_gradient
    state = _rect("legend-swatch:planned:opaque-state-key", kind="Symbol", fill=key_fill,
                  bounds={"inline": 100, "block": 20, "inlineSize": 10, "blockSize": 10},
                  source_ref="opaque-state-key", stroke=key_stroke)
    state.update(sourceKind="legend", purpose="legend-swatch", visualRole="planned",
                 paint=state_paint,
                 legendEncodingCoverage={"kind": "state", "witnesses": deepcopy(witnesses)})
    primitives.append(state)

    scale = _rect("legend-swatch:encoding:opaque-scale-key", kind="Rect", fill=scale_fill,
                  source_ref="opaque-scale-key")
    scale.update(sourceKind="legend", purpose="legend-swatch", visualRole="planned",
                 legendEncodingCoverage={"kind": "encoding", "witnesses": deepcopy(witnesses)})
    primitives.append(scale)
    return _scene(primitives)


def test_encoded_point_key_accepts_only_typed_reciprocal_coverage_and_fill_neutralization():
    scene = _neutral_encoded_point_scene()
    assert legend_key_findings(scene) == []


def test_exact_paint_match_remains_good_but_declared_coverage_still_needs_its_scale_key():
    exact = _neutral_encoded_point_scene(key_fill="#AA0000")
    assert legend_key_findings(exact) == []

    exact["surfaces"][0]["primitives"].pop()
    assert any("separate encoding key" in finding for finding in legend_key_findings(exact))


def test_neutral_point_key_can_restore_theme_gradient_only_with_exact_coverage():
    gradient = {"start": {"x": 0, "y": 0}, "end": {"x": 0, "y": 1},
                "stops": [{"offset": 0, "color": "#FFFFFF"},
                          {"offset": 1, "color": "#333333"}], "fidelity": "required"}
    scene = _neutral_encoded_point_scene(key_gradient=gradient)
    assert legend_key_findings(scene) == []

    without_coverage = deepcopy(scene)
    without_coverage["surfaces"][0]["primitives"][1].pop("legendEncodingCoverage")
    assert any("typed state coverage" in finding for finding in legend_key_findings(without_coverage))


def test_hollow_theme_state_key_keeps_stroke_and_uses_filled_encoding_key():
    scene = _neutral_encoded_point_scene()
    state = scene["surfaces"][0]["primitives"][1]
    state["paint"]["fill"] = None
    assert legend_key_findings(scene) == []


def test_encoded_fill_neutralization_keeps_pattern_ink_unchanged():
    scene = _neutral_encoded_point_scene()
    source, state = scene["surfaces"][0]["primitives"][:2]
    pattern = {"kind": "hatch", "spacing": 4, "angle": 45,
               "stroke": "#101010", "strokeWidth": 1}
    source["pattern"] = deepcopy(pattern)
    state["pattern"] = deepcopy(pattern)
    assert legend_key_findings(scene) == []

    state["pattern"]["spacing"] = 5
    assert any("complete source figure" in finding for finding in legend_key_findings(scene))


@pytest.mark.parametrize("mutation,expected", [
    ("missing-state", "typed state coverage"),
    ("forged-value", "source figure"),
    ("wrong-scale", "source figure"),
    ("wrong-field", "source figure"),
    ("wrong-origin", "source figure"),
    ("same-key-only", "separate encoding key"),
    ("cross-surface", "separate encoding key"),
    ("wrong-scale-fill", "separate encoding key"),
    ("nonfill-stroke", "complete source figure"),
])
def test_encoded_point_key_rejects_incomplete_or_forged_coverage(mutation, expected):
    scene = _neutral_encoded_point_scene()
    surfaces = scene["surfaces"]
    primitives = surfaces[0]["primitives"]
    if mutation == "missing-state":
        primitives[1].pop("legendEncodingCoverage")
    elif mutation in {"forged-value", "wrong-scale", "wrong-field", "wrong-origin"}:
        witness = primitives[1]["legendEncodingCoverage"]["witnesses"][0]
        if mutation == "forged-value":
            witness["value"] = "closed"
        elif mutation == "wrong-scale":
            witness["scaleId"] = "other-scale"
        elif mutation == "wrong-field":
            witness["field"] = "other-field"
        else:
            witness["sources"][0]["id"] = "other-view"
    elif mutation == "same-key-only":
        primitives.pop()
    elif mutation == "cross-surface":
        encoding = primitives.pop()
        surfaces.append({"primitives": [encoding]})
    elif mutation == "wrong-scale-fill":
        primitives[-1]["paint"]["fill"] = "#00AA00"
    else:
        primitives[1]["paint"]["stroke"] = "#FFFFFF"
    assert any(expected in finding for finding in legend_key_findings(scene)), legend_key_findings(scene)


def test_encoding_other_coverage_can_represent_many_raw_values_with_one_fill():
    witnesses = [_fill_witness("rare-a"), _fill_witness("rare-b")]
    scene = _neutral_encoded_point_scene(witnesses)
    assert legend_key_findings(scene) == []

    broken = deepcopy(scene)
    broken["surfaces"][0]["primitives"][-1]["legendEncodingCoverage"]["witnesses"].pop()
    assert any("separate encoding key" in finding
               for finding in legend_key_findings(broken))


def test_encoding_coverage_does_not_assign_another_part_fill_to_a_witness():
    witness_a, witness_b = _fill_witness("a"), _fill_witness("b")
    scene = _neutral_encoded_point_scene([witness_a])
    encoding = scene["surfaces"][0]["primitives"][-1]
    encoding["visualRole"] = "unclassified-custom-role"
    assert legend_key_findings(scene) == []
    encoding["legendEncodingCoverage"]["witnesses"] = [witness_a]
    extra = _rect("legend-swatch:encoding:other-part", kind="Rect", fill="#AA0000")
    extra.update(sourceKind="legend", purpose="legend-swatch",
                 visualRole="unclassified-custom-role",
                 legendEncodingCoverage={"kind": "encoding", "witnesses": [witness_b]})
    # The correct source fill belongs only to witness b's part; it cannot prove a.
    encoding["paint"]["fill"] = "#00AA00"
    scene["surfaces"][0]["primitives"].append(extra)
    assert any("separate encoding key" in finding for finding in legend_key_findings(scene))


def test_encoded_neutralization_does_not_ignore_explicit_multipart_paint():
    witness = _fill_witness()
    bounds = {"inline": 10, "block": 20, "inlineSize": 10, "blockSize": 10}
    source = _rect("planned:opaque-object:part0", kind="Symbol", fill="#AA0000",
                   bounds=bounds, source_ref="object", stroke="#111111")
    source.update(sourceKind="object", purpose="planned", visualRole="planned", encoding=witness)
    explicit = _rect("planned:opaque-object:part1", kind="Symbol", fill="#00AA00",
                     bounds=bounds, source_ref="object", stroke="#222222")
    explicit.update(sourceKind="object", purpose="planned", visualRole="planned")
    state0 = _rect("legend-swatch:planned:key:part0", kind="Symbol", fill="#333333",
                   bounds=bounds, source_ref="key", stroke="#111111")
    state0.update(sourceKind="legend", purpose="legend-swatch", visualRole="planned",
                  legendEncodingCoverage={"kind": "state", "witnesses": [witness]})
    state1 = _rect("legend-swatch:planned:key:part1", kind="Symbol", fill="#00AA00",
                   bounds=bounds, source_ref="key", stroke="#222222")
    state1.update(sourceKind="legend", purpose="legend-swatch", visualRole="planned")
    scale = _rect("legend-swatch:encoding:key", kind="Rect", fill="#AA0000")
    scale.update(sourceKind="legend", purpose="legend-swatch", visualRole="planned",
                 legendEncodingCoverage={"kind": "encoding", "witnesses": [witness]})
    scene = _scene([source, explicit, state0, state1, scale])
    assert legend_key_findings(scene) == []

    broken = deepcopy(scene)
    broken["surfaces"][0]["primitives"][3]["paint"]["fill"] = "#FFFFFF"
    assert any("complete source figure" in finding
               for finding in legend_key_findings(broken))


def test_coincident_planned_and_actual_multipart_figures_do_not_form_a_hybrid():
    bounds = {"inline": 12, "block": 20, "inlineSize": 10, "blockSize": 10}

    def part(identifier, source, role, fill, stroke=None, *, legend=False):
        item = _rect(identifier, kind="Symbol", fill=fill, stroke=stroke,
                     bounds=bounds, source_ref=source)
        item.update(purpose="legend-swatch" if legend else role, visualRole=role)
        item["sourceKind"] = "legend" if legend else "object"
        return item

    scene = _scene([
        part("planned:gate-a:part0", "same-source", "gate", "#AA0000"),
        part("planned:gate-a:part1", "same-source", "gate", None, "#111111"),
        part("actual:gate-a:part0", "same-source", "actual", "#0000AA"),
        part("actual:gate-a:part1", "same-source", "actual", None, "#EEEEEE"),
        part("legend-swatch:milestone:planned-key:part0", "planned-key", "gate", "#AA0000", legend=True),
        part("legend-swatch:milestone:planned-key:part1", "planned-key", "gate", None, "#111111", legend=True),
        part("legend-swatch:milestone:actual-key:part0", "actual-key", "actual", "#0000AA", legend=True),
        part("legend-swatch:milestone:actual-key:part1", "actual-key", "actual", None, "#EEEEEE", legend=True),
    ])
    assert legend_key_findings(scene) == []

    hybrid = deepcopy(scene)
    # Each component exists in the coincident source figures, but this mix
    # is not the complete paint stack of either one.
    hybrid["surfaces"][0]["primitives"][-3]["paint"]["stroke"] = "#EEEEEE"
    assert any("complete figure" in finding for finding in legend_key_findings(hybrid))


def _glow_point_key_scene() -> dict:
    source_bounds = {"inline": 1029.2, "block": 396.8,
                     "inlineSize": 24, "blockSize": 24}
    key_bounds = {"inline": 1396, "block": 771.338,
                  "inlineSize": 24, "blockSize": 24}

    def glow_paint(region_inline, region_block):
        return {"fill": "#FF7A1A", "stroke": "#0A0A0C", "strokeWidth": 1,
                "dash": [], "opacity": 1,
                "glow": {"color": "#FFB52E", "blur": 7, "opacity": .85,
                         "fidelity": "required",
                         "region": {"inline": region_inline, "block": region_block,
                                    "inlineSize": 66, "blockSize": 66}}}

    source = _rect("planned:evb-arrival", kind="Symbol", fill="#FF7A1A",
                   bounds=source_bounds, source_ref="evb-arrival")
    source.update(sourceKind="object", purpose="planned", visualRole="planned",
                  paint=glow_paint(1008.2, 375.8))
    key = _rect("legend-swatch:planned:opaque-digest", kind="Symbol", fill="#FF7A1A",
                bounds=key_bounds, source_ref="planned:opaque-digest")
    key.update(sourceKind="legend", purpose="legend-swatch", visualRole="planned",
               paint=glow_paint(1375, 750.338))
    return _scene([source, key])


def test_point_key_glow_region_matches_by_physical_padding():
    assert legend_key_findings(_glow_point_key_scene()) == []


@pytest.mark.parametrize("mutation", [
    "fill", "glow-color", "glow-blur", "glow-opacity", "glow-fidelity", "glow-padding",
])
def test_point_key_glow_match_still_rejects_changed_paint_or_effect(mutation):
    scene = _glow_point_key_scene()
    key = scene["surfaces"][0]["primitives"][1]
    glow = key["paint"]["glow"]
    if mutation == "fill":
        key["paint"]["fill"] = "#123456"
    elif mutation == "glow-color":
        glow["color"] = "#123456"
    elif mutation == "glow-blur":
        glow["blur"] += 1
    elif mutation == "glow-opacity":
        glow["opacity"] -= .1
    elif mutation == "glow-fidelity":
        glow["fidelity"] = "best-effort"
    else:
        glow["region"]["inlineSize"] += 1
    assert any("complete figure" in finding for finding in legend_key_findings(scene))


def test_planned_progress_does_not_require_an_actual_progress_key():
    scene = _scene([
        _rect("planned:campaign"),
        _rect("legend-swatch:planned"),
        _rect("progress-fill:planned:campaign"),
        _rect("legend-swatch:progressFill:progress-ink"),
        _rect("legend-swatch:actual"),
    ])
    assert legend_key_findings(scene) == []


@pytest.mark.parametrize("role", ["planned", "actual"])
def test_positive_progress_requires_a_separate_progress_key(role):
    scene = _scene([_rect(f"{role}:host"), _rect(f"legend-swatch:{role}"),
                    _rect(f"progress-fill:{role}:host", fill="#D09030")])
    findings = legend_key_findings(scene)
    assert any("Progress" in finding and "separate" in finding for finding in findings)


@pytest.mark.parametrize("role", ["planned", "actual"])
def test_progress_key_paint_matches_positive_progress_marks(role):
    fill = _rect(f"progress-fill:{role}:host", fill="#D09030")
    key = _rect("legend-swatch:progressFill:progress-ink", fill="#D09030")
    fill["paint"]["stroke"] = key["paint"]["stroke"] = "#123456"
    scene = _scene([_rect(f"{role}:host"), _rect(f"legend-swatch:{role}"), fill, key])
    assert legend_key_findings(scene) == []

    broken = deepcopy(scene)
    broken["surfaces"][0]["primitives"][-1]["paint"]["fill"] = None
    findings = legend_key_findings(broken)
    assert any("progress" in finding.lower() and "paint" in finding.lower()
               for finding in findings)

    broken = deepcopy(scene)
    broken["surfaces"][0]["primitives"][-1]["paint"]["stroke"] = "#ABCDEF"
    assert any("progress" in finding.lower() and "paint" in finding.lower()
               for finding in legend_key_findings(broken))


def test_same_host_fill_progress_is_redundant_even_when_borders_differ():
    host = _rect("actual:host", fill="#B06020", stroke="#222222", source_ref="task")
    progress = _rect("progress-fill:actual:host", fill="#B06020", stroke="#FFFFFF",
                     source_ref="task")
    assert legend_key_findings(_scene([host, progress])) == []

    distinct = deepcopy(progress)
    distinct["paint"]["fill"] = "#D09030"
    assert any("no separate Progress key" in item for item in legend_key_findings(_scene([host, distinct])))


def test_progress_cannot_borrow_same_color_from_unrelated_host():
    host = _rect("actual:host-a", fill="#B06020")
    unrelated = _rect("actual:host-b", fill="#B06020")
    progress = _rect("progress-fill:actual:host-a", fill="#D09030")
    progress["clipSourceId"] = "actual:missing-host"
    findings = legend_key_findings(_scene([host, unrelated, progress]))
    assert any("no separate Progress key" in item for item in findings)


def test_distinct_progress_without_a_declared_legend_slot_needs_no_key():
    surface = {"slots": [{"id": "timeline", "source": "timeline"}],
               "primitives": [_rect("planned:host", fill="#B06020"),
                              _rect("progress-fill:planned:host", fill="#D09030")]}
    assert legend_key_findings({"surfaces": [surface]}) == []


def test_distinct_progress_with_a_declared_legend_slot_needs_key():
    surface = {"slots": [{"id": "legend", "source": "legend"}],
               "primitives": [_rect("planned:host", fill="#B06020"),
                              _rect("progress-fill:planned:host", fill="#D09030")]}
    assert any("no separate Progress key" in item for item in legend_key_findings({"surfaces": [surface]}))


def test_each_actual_paint_group_matches_some_actual_mark_not_only_the_first():
    scene = _scene([
        _rect("actual:first", fill="#AA0000"),
        _rect("actual:second", fill="#0000AA"),
        _rect("legend-swatch:actual:paint-red", fill="#AA0000"),
        _rect("legend-swatch:actual:paint-blue", fill="#0000AA"),
    ])
    assert legend_key_findings(scene) == []

    broken = deepcopy(scene)
    broken["surfaces"][0]["primitives"][-1]["paint"]["fill"] = "#00AA00"
    assert any("no Actual mark" in finding for finding in legend_key_findings(broken))

def test_path_key_bounds_must_enclose_its_points():
    path = {"id": "legend-swatch:dependency", "kind": "Path",
            "bounds": {"inline": 0, "block": 0, "inlineSize": 10, "blockSize": 5},
            "points": [[1, 1], [9, 4]]}
    assert legend_key_findings(_scene([path])) == []

    broken = deepcopy(path)
    broken["bounds"]["inlineSize"] = 0
    findings = legend_key_findings(_scene([broken]))
    assert any("dependency" in finding and "enclose" in finding.lower() for finding in findings)


def test_legend_findings_cover_each_surface_not_only_the_first():
    clean = [_rect("planned:host"), _rect("legend-swatch:planned")]
    broken = [_rect("scenario:host"), _rect("legend-swatch:scenario", kind="Symbol")]
    findings = legend_key_findings(_scene(clean, broken))
    assert any("scenario" in finding and "shape" in finding.lower() for finding in findings)


def _write_manifest_scene(root: Path, *, scene_payload: str = '{"surfaces": [{"primitives": []}]}') -> Path:
    deck = root / "examples" / "sample"
    (deck / "generated").mkdir(parents=True)
    (deck / "manifest.yaml").write_text(
        "version: chrona/example-materializer/v0.1\nid: sample\nrole: regression-corpus\n"
        "context: context.yaml\nslides:\n  - id: one\n    context: context.yaml\n"
        "    expectedSvg: generated/one.svg\n    expectedScene: generated/one.scene.json\n",
        encoding="utf-8")
    scene = deck / "generated" / "one.scene.json"
    scene.write_text(scene_payload, encoding="utf-8")
    (deck / "generated" / "orphan.scene.json").write_text(
        '{"surfaces": [{"primitives": []}]}', encoding="utf-8")
    return scene


def test_committed_scene_discovery_uses_manifest_targets_only(tmp_path):
    declared = _write_manifest_scene(tmp_path)

    assert checker.committed_scene_paths(tmp_path) == (declared.resolve(),)


def test_corpus_gate_reports_a_malformed_declared_scene_structurally(tmp_path, monkeypatch, capsys):
    scene = _write_manifest_scene(tmp_path, scene_payload='{"surfaces": [{}]}')
    monkeypatch.setattr(checker, "committed_scene_paths", lambda root=checker.ROOT: (scene,))
    evaluate = checker.evaluate_committed_scenes
    monkeypatch.setattr(checker, "evaluate_committed_scenes",
                        lambda paths, *, root=checker.ROOT: evaluate(paths, root=tmp_path))

    assert checker.main() == 1
    report = json.loads(capsys.readouterr().out)
    assert report["errorCount"] == 1
    assert report["findings"] == [{
        "scene": scene.relative_to(tmp_path).as_posix(),
        "finding": "E_LEGEND_KEY_DOCUMENT:'primitives'",
    }]
