"""Real projection/composer acceptance fixtures for relation entry routing (#1120 / #1109 R4)."""
from copy import deepcopy
from dataclasses import replace
from datetime import date
from decimal import Decimal

import pytest

import chrona.presentation.layout.surface_routes as surface_routes
import chrona.presentation.layout.routing as routing
import chrona.presentation.layout.ports as route_ports
import tests.unit.chrona.presentation.scene.test_relation_node_approach as node_approach
from chrona.presentation.contracts.resources import ViewWindow
from chrona.presentation.layout.sources import MeasuredSources, SourceInput
from chrona.presentation.model.projection import build_review_projection
from chrona.presentation.scene.v05_builder import build_scene_input, compose_review_surface

from tests.unit.chrona.presentation.scene.test_relation_ghost_endpoints import PROJECT as PROJECT_BASE, _view
from tests.unit.chrona.presentation.scene.test_v05_builder import (
    _Font, _manifest, _theme, _title_measurement, surface_content,
)


WINDOW = ViewWindow("explicit", "2026-01-01", "2026-06-16", 0)
RELATION = {"id": "dep", "type": "dependency",
            "from": {"object": "a", "endpoint": "end"},
            "to": {"object": "b", "endpoint": "start"}}
PLACED = {
    "a": {"start": date(2026, 2, 1), "end": date(2026, 2, 8)},
    "b": {"start": date(2026, 2, 12), "end": date(2026, 2, 20)},
}
ACTUAL = {"observations": [{"id": "a-observation", "sequence": 1, "projectObjectId": "a",
                            "actual": {"start": "2026-02-01", "finish": "2026-02-09"}}]}


def _project(*, mirrored=False, baseline_ghost=False, ghost_finish=11):
    project = {**PROJECT_BASE, "relations": [deepcopy(RELATION)]}
    placed = dict(PLACED)
    actual = {"observations": [dict(ACTUAL["observations"][0])]}
    if mirrored:
        placed = {
            "a": {"start": date(2026, 2, 12), "end": date(2026, 2, 20)},
            "b": {"start": date(2026, 2, 1), "end": date(2026, 2, 8)},
        }
        actual["observations"][0]["actual"] = {"start": "2026-02-11", "finish": "2026-02-21"}
        project["relations"][0]["from"]["endpoint"] = "start"
        project["relations"][0]["to"]["endpoint"] = "end"
    view = _view("automatic")
    comparison = view.comparison
    if not baseline_ghost:
        comparison = replace(comparison, baseline=None, baseline_marks=None)
    view = replace(view, window=WINDOW, comparison=comparison)
    snapshot = None
    snapshot_placements = None
    if baseline_ghost:
        snapshot = project
        # A real baseline instance of b, detached from both relation endpoints, sits inside the temporal gap.
        snapshot_placements = {"b": {"start": date(2026, 2, ghost_finish - 1),
                                      "end": date(2026, 2, ghost_finish)}}
    projection = build_review_projection(project, placed, view, actual,
        snapshot_project=snapshot, snapshot_placements=snapshot_placements)
    return project, placed, actual, view, projection


def _theme_with_route_fixture_geometry(*, target_marker="triangle"):
    """Keep every mark fraction in range while giving the actual its measured nested offset."""
    theme = _theme()
    values = theme["body"]["values"]
    # At a 20px track slot: planned is 8px at offset 6px; actual is 3.36px at offset 14.8px.
    # This puts the observed mark 8.8px below the plan mark, matching the intended blocker geometry.
    values["mark-full"]["value"] = 0.4
    values["mark-start"]["value"] = 0.3
    values["mark-content"]["value"] = 0.168
    values["mark-nested"]["value"] = 0.74
    values["dependency-marker"]["value"]["shape"] = target_marker
    return theme


def _compose(*, mirrored=False, baseline_ghost=False, entry="side-when-free", target_marker="triangle",
             ghost_finish=11, corner_radius=0, head_length=10):
    project, placed, actual, view, projection = _project(mirrored=mirrored, baseline_ghost=baseline_ghost,
                                                     ghost_finish=ghost_finish)
    metrics = {
        "text.body.size": Decimal(14), "text.body.lineHeight": Decimal("1.4"),
        "timeline.row.minBlockSize": Decimal(22), "timeline.row.paddingBlock": Decimal(0),
        "timeline.mark.blockSize": Decimal(20),
        "timeline.relation.cornerRadius": Decimal(corner_radius),
    }
    measured = MeasuredSources({"title": _title_measurement()}, {"title": SourceInput(("Plan",))}, metrics)
    manifest = replace(_manifest("title", "table", "timeline", "timeline-axis"),
        relation_entry=entry, row_distribution="pack", relation_max_bends=4, relation_max_detour_ratio=2)
    content = surface_content(relations=project["relations"], show_member_labels=True, label_placement="plot",
        label_content=("title",), label_side="end", label_overflow="visible-overflow")
    theme = _theme_with_route_fixture_geometry(target_marker=target_marker)
    theme["body"]["values"]["dependency-marker"]["value"]["headLength"] = head_length
    value = build_scene_input(projection=projection, surface_content=content, layout_manifest=manifest,
        resolved_theme=theme,
        font_metrics=_Font(), measured_sources=measured,
        capabilities={"svg": True})
    return compose_review_surface(value)


@pytest.mark.parametrize("radius", range(7))
def test_clipped_corner_preserves_head_and_side_entry_beside_detached_ghost(radius):
    surface = _compose(baseline_ghost=True, ghost_finish=9, entry="side",
                       corner_radius=radius, head_length=6)
    path = _relation_path(surface)
    assert path.points[-2][1] == path.points[-1][1]
    assert path.points[-1][0] - path.points[-2][0] >= 7 - 1e-6
    ghost = next(p for p in surface.primitives if p.scene_id == "planned:b:snapshot:b")
    assert path.points[-2][0] >= ghost.bounds[0] + ghost.bounds[2]
    assert not any("ENTRY_FALLBACK" in diagnostic for diagnostic in surface.diagnostics)
    # The adapter receives a full straight head tangent after the completed turn.
    assert not radius or path.path_commands[-1].kind == "line"
    previous = path.path_commands[-2].points[-1] if path.path_commands else path.points[-2]
    endpoint = path.path_commands[-1].points[-1] if path.path_commands else path.points[-1]
    assert endpoint[0] - previous[0] >= 6 - 1e-6


def test_radius_clipping_does_not_shorten_a_head_to_cross_a_detached_ghost():
    surface = _compose(baseline_ghost=True, ghost_finish=11, entry="side",
                       corner_radius=4, head_length=6)
    assert any("reason=entry-stub-blocked" in diagnostic for diagnostic in surface.diagnostics)


def _relation_path(surface):
    paths = [item for item in surface.primitives
             if item.kind == "Path" and item.scene_id.startswith("relation:")]
    assert len(paths) == 1, [item.scene_id for item in paths]
    return paths[0]


def _bends(points):
    return sum((a[0] == b[0]) != (b[0] == c[0])
               for a, b, c in zip(points, points[1:], points[2:]))


def _path_crosses_rect(points, bounds):
    left, top, width, height = bounds
    right, bottom = left + width, top + height
    for (x1, y1), (x2, y2) in zip(points, points[1:]):
        if y1 == y2 and top < y1 < bottom and max(x1, x2) > left and min(x1, x2) < right:
            return True
        if x1 == x2 and left < x1 < right and max(y1, y2) > top and min(y1, y2) < bottom:
            return True
    return False


def _prior_source_first(monkeypatch):
    """Restore the prior pair order and first-eligible policy for a negative regression check."""
    original = surface_routes.select_relation_route

    def select_first_eligible(pairs, **kwargs):
        kwargs.pop("rank", None)
        return original(pairs, **kwargs)

    monkeypatch.setattr(surface_routes, "stub_pairs_first", lambda pairs: pairs)
    monkeypatch.setattr(surface_routes, "select_relation_route", select_first_eligible)


def test_nearest_stub_exit_can_be_rejected_before_the_other_exit_enters_horizontally(monkeypatch):
    attempts = []
    nearest_candidates = []
    original = surface_routes.select_relation_route
    original_pair = routing._select_pair_candidate
    original_measure = routing.route_quality_attempt

    def measure(*args, **kwargs):
        result = original_measure(*args, **kwargs)
        nearest_candidates.append(result)
        return result

    def capture_nearest(source, target, **kwargs):
        if source.side == "below" and target.stub:
            with monkeypatch.context() as local:
                local.setattr(routing, "route_quality_attempt", measure)
                return original_pair(source, target, **kwargs)
        return original_pair(source, target, **kwargs)

    def capture(pairs, **kwargs):
        result = original(pairs, **kwargs)
        attempts.extend(result.attempts)
        return result

    monkeypatch.setattr(surface_routes, "select_relation_route", capture)
    monkeypatch.setattr(routing, "_select_pair_candidate", capture_nearest)
    current = _compose()
    points = _relation_path(current).points
    assert _bends(points) == 4
    assert points[-2][1] == points[-1][1] and points[-2][0] < points[-1][0]
    assert points[-1][0] - points[-2][0] >= 11
    assert nearest_candidates[0].bends == 5
    assert min(item.bends for item in nearest_candidates
               if item.length <= item.direct_length * item.max_detour_ratio) == 5
    assert attempts[0].source_side == "below" and attempts[0].outcome == "quality-rejected"
    assert (attempts[1].source_side, attempts[1].outcome, attempts[1].bends) == ("end", "accepted", 4)

    with monkeypatch.context() as old:
        _prior_source_first(old)
        prior = _relation_path(_compose()).points
    assert _bends(prior) == 2
    assert prior[-2][0] == prior[-1][0], "the previous source-first rule takes the vertical target entry"


def test_actual_finish_delta_text_and_detached_snapshot_ghost_are_real_scene_content(monkeypatch):
    surface = _compose(baseline_ghost=True, entry="side")
    path = _relation_path(surface)
    variance = next(item for item in surface.primitives if item.scene_id == "variance:a:a")
    assert variance.kind == "Text" and variance.text == "+1d"
    actual = next(item for item in surface.primitives if item.scene_id == "actual:a:a")
    assert abs((variance.bounds[0] + variance.bounds[2])
               - (actual.bounds[0] + actual.bounds[2])) < 3
    ghost = next(item for item in surface.primitives if item.scene_id == "planned:b:snapshot:b")
    target = next(item for item in surface.primitives if item.scene_id == "planned:b:b")
    stub_tip = float(target.bounds[0]) - 11
    target_start = float(target.bounds[0])
    target_y = float(target.bounds[1] + target.bounds[3] / 2)
    assert ghost.bounds[0] < target_start and ghost.bounds[0] + ghost.bounds[2] > stub_tip
    assert ghost.bounds[1] < target_y < ghost.bounds[1] + ghost.bounds[3]
    assert not _path_crosses_rect(path.points, ghost.bounds), "the detached snapshot remains a route obstacle"
    assert any(item == f"I_LAYOUT_RELATION_ENTRY_FALLBACK:{path.scene_id};reason=entry-stub-blocked"
               for item in surface.diagnostics)

    original_overlap = route_ports._overlaps
    with monkeypatch.context() as old:
        old.setattr(route_ports, "_overlaps", lambda left, right:
                    left.source_ref == right.source_ref or original_overlap(left, right))
        legacy = _compose(baseline_ghost=True, entry="side")
    legacy_path = _relation_path(legacy)
    legacy_ghost = next(item for item in legacy.primitives if item.scene_id == "planned:b:snapshot:b")
    assert _path_crosses_rect(legacy_path.points, legacy_ghost.bounds), (
        "the prior all-same-object host exemption lets the route cross the detached baseline ghost")


def test_the_mirrored_end_entry_keeps_the_full_horizontal_stub_and_old_order_does_not(monkeypatch):
    current = _compose(mirrored=True)
    points = _relation_path(current).points
    assert points[-2][1] == points[-1][1] and points[-2][0] > points[-1][0]
    assert points[-2][0] - points[-1][0] >= 11

    _prior_source_first(monkeypatch)
    prior = _relation_path(_compose(mirrored=True)).points
    assert prior[-2][0] == prior[-1][0], "prior order drops vertically onto the target end"


def test_round_target_terminal_keeps_semantic_entry_stub_after_paint_trimming():
    surface = _compose(entry="side", target_marker="circle")
    path = _relation_path(surface)
    target = next(item for item in surface.primitives if item.scene_id == "planned:b:b")
    marker = path.marker_end
    target_center = (target.bounds[0], target.bounds[1] + target.bounds[3] / 2)
    assert marker is not None and marker.centred and marker.head_length == 10
    assert path.points[-1] == pytest.approx((target_center[0] - marker.head_length / 2, target_center[1]))
    assert not any(item.startswith(f"I_LAYOUT_RELATION_ENTRY_FALLBACK:{path.scene_id};")
                   for item in surface.diagnostics)
    # Paint trimming consumes the five-pixel radius, but the semantic path still reserves its 11px stub.
    assert path.points[-1][0] - path.points[-2][0] == pytest.approx(6)
    semantic_stub = target_center[0] - path.points[-2][0]
    assert semantic_stub >= marker.head_length + 1


@pytest.mark.parametrize("radius", range(7))
def test_gate_bottom_back_route_avoids_arrival_without_false_node_conflict(monkeypatch, radius):
    original = node_approach.build_scene_input

    def side_entry(*args, **kwargs):
        kwargs["layout_manifest"] = replace(kwargs["layout_manifest"], relation_entry="side")
        theme = deepcopy(kwargs["resolved_theme"])
        theme["body"]["values"]["dependency-marker"]["value"].update(headLength=6, headWidth=6)
        theme["body"]["values"]["no-source"] = {"type": "marker", "value": {
            "shape": "none", "headLength": 6, "headWidth": 6, "attachmentOffset": 0}}
        theme["body"]["roles"]["relationSourceTerminal"] = {"marker": "no-source"}
        kwargs["resolved_theme"] = theme
        measured = kwargs["measured_sources"]
        kwargs["measured_sources"] = replace(measured, metric_values={**measured.metric_values,
            "timeline.relation.cornerRadius": Decimal(radius)})
        return original(*args, **kwargs)

    monkeypatch.setattr(node_approach, "build_scene_input", side_entry)
    incoming = {**node_approach.INCOMING, "to": {"object": "g", "endpoint": "start"}}
    paths, marks, diagnostics = node_approach._gate_chain(
        (incoming, node_approach.OUTGOING), gap=-1)
    assert node_approach._terminal_segment_residuals(paths) == set()
    outgoing = next(path for path in paths if path.source_ref == "g-l")
    assert outgoing.points[0][0] == outgoing.points[1][0]
    assert outgoing.points[0][1] == pytest.approx(marks["g:g"].bounds[1] + marks["g:g"].bounds[3])
    assert outgoing.points[-1][1] == outgoing.points[-2][1]
    assert outgoing.points[-1][0] - outgoing.points[-2][0] >= 7 - 1e-6
    assert not any("ENTRY_FALLBACK" in diagnostic for diagnostic in diagnostics)
