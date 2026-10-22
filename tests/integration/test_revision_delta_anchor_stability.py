"""#1300: actual Scene/SVG revision evidence from project-independent fixtures."""
from datetime import date, timedelta
from dataclasses import replace
from decimal import Decimal
import xml.etree.ElementTree as ET
import yaml
import pytest

from chrona.presentation.layout import surface_composer
from chrona.presentation.layout.model import Rect
from chrona.presentation.layout.ports import connector_egress_candidates
from chrona.presentation.model.info_diagnostics import RelationHintReceipt, RelationResolutionInfo
from chrona.presentation.layout.surface_quality import MarkPlacement
from chrona.presentation.scene.serialization import serialize_scene
from chrona.resources import builtin_preset_source_root, safe_load
from chrona.usecases.draft_render import DraftRenderRequest, render_draft
from tests.support import synthetic_review as sr


def _render(directory, *, shift=0, append=False, previous_scene=None, delta_unit=None,
            source_actual_finish=None, target_actual_start=None):
    directory.mkdir()
    move = timedelta(days=shift)
    source = sr.with_calendar(sr.project({
        "source": sr.span("source", date(2027, 1, 4) + move, 10),
        "target": sr.span("target", date(2027, 2, 1) + move, 10),
    }, [{"id": "source-target", "type": "dependency", "lag": "0d",
         "from": {"object": "source", "endpoint": "end"},
         "to": {"object": "target", "endpoint": "start"}}]))
    actual_source_finish = (source_actual_finish + move if source_actual_finish is not None
                            else date(2027, 1, 17) + move)
    actual_target_start = (target_actual_start + move if target_actual_start is not None
                           else date(2027, 2, 1) + move)
    if append:
        source["objects"]["unrelated"] = sr.span("unrelated", date(2027, 1, 20), 5)
    actual = {"version": "chrona/actual-set/v0.3", "kind": "actual-set", "id": "actuals", "body": {
        "asOf": (date(2027, 2, 20) + move).isoformat(), "observations": [
            {"id": "source-done", "sequence": 1, "projectObjectId": "source", "actual": {
                "start": (date(2027, 1, 4) + move).isoformat(),
                "finish": actual_source_finish.isoformat(), "progress": 1}},
            {"id": "target-done", "sequence": 1, "projectObjectId": "target", "actual": {
                "start": actual_target_start.isoformat(),
                "finish": (date(2027, 2, 9) + move).isoformat(), "progress": 1}},
        ]}}
    project_path, actual_path = directory / "project.yaml", directory / "actual.yaml"
    project_path.write_text(yaml.safe_dump(source, sort_keys=False), encoding="utf-8")
    actual_path.write_text(yaml.safe_dump(actual, sort_keys=False), encoding="utf-8")
    view_path = None
    if delta_unit is not None:
        view = safe_load(builtin_preset_source_root("presets/bundles/editorial-readable-default")
                         .joinpath("view.yaml").read_bytes())
        view["body"]["comparison"]["deltaUnit"] = delta_unit
        view_path = directory / "view.yaml"
        view_path.write_text(yaml.safe_dump(view, sort_keys=False), encoding="utf-8")
    return render_draft(DraftRenderRequest(project_path, "svg", actual=actual_path,
                                           previous_scene=previous_scene, view=view_path)).rendered


def _relation_routes(rendered):
    return {
        (item.source_ref, item.from_instance_id, item.to_instance_id): item
        for item in rendered.surface.primitives
        if item.kind == "Path" and item.source_kind == "relation"
        and item.from_instance_id and item.to_instance_id
    }


def _anchor_sides(rendered):
    primitives = {item.scene_id: item for item in rendered.surface.primitives}
    sides = {}
    for identity, delta in primitives.items():
        if not identity.startswith("variance:") or delta.kind != "Text":
            continue
        object_id = identity.removeprefix("variance:")
        mark = primitives.get(f"actual:{object_id}") or primitives[f"planned:{object_id}"]
        x, y, width, height = delta.bounds
        left, top, inline, block = mark.bounds
        if x >= left + inline:
            side = "end"
        elif x + width <= left:
            side = "start"
        elif y + height <= top:
            side = "above"
        elif y >= top + block:
            side = "below"
        else:
            raise AssertionError(f"detached/overlapping delta {identity}: {delta.bounds}, {mark.bounds}")
        sides[identity] = side
    assert set(sides) == {"variance:source:source", "variance:target:target"}
    return sides


def _suppressed_relations(rendered):
    return {item for item in rendered.scene.diagnostics if item.startswith("W_LAYOUT_RELATION_SUPPRESSED:")}


def _crosses_mark(route, mark):
    left, top, width, height = mark.bounds
    right, bottom = left + width, top + height
    for (x1, y1), (x2, y2) in zip(route.points, route.points[1:]):
        if y1 == y2 and top < y1 < bottom and max(min(x1, x2), left) < min(max(x1, x2), right):
            return True
        if x1 == x2 and left < x1 < right and max(min(y1, y2), top) < min(max(y1, y2), bottom):
            return True
    return False


def _assert_connected_actual_endpoint_corridor(rendered):
    route, = _relation_routes(rendered).values()
    primitives = {item.scene_id: item for item in rendered.surface.primitives}
    planned, actual = primitives["planned:source:source"], primitives["actual:source:source"]

    def placement(item):
        inline, block, inline_size, block_size = item.bounds
        bounds = Rect(*(Decimal(str(value)) for value in
                        (inline, block, inline_size, block_size)))
        center = (inline, block + block_size / 2)
        return MarkPlacement(item.scene_id, item.source_ref, bounds, center,
                             (inline + inline_size, center[1]),
                             semantic_id=item.purpose, mark_shape="span")

    planned_mark, actual_mark = placement(planned), placement(actual)
    candidate, = [item for item in connector_egress_candidates(
        planned_mark, "end", route.points[-1], (actual_mark,)) if item.side == "end"]
    assert candidate.host_ids == ("actual:source:source", "planned:source:source")
    assert candidate.semantic_port == planned_mark.end_port
    assert candidate.exposed_port == pytest.approx((
        float(actual_mark.bounds.inline + actual_mark.bounds.inline_size),
        planned_mark.end_port[1],
    ))
    # Layout's first visible segment is the terminal-tangent continuation of
    # this exact named corridor, and the next vertex is its recorded boundary.
    assert route.points[0][1] == candidate.semantic_port[1]
    assert candidate.semantic_port[0] <= route.points[0][0] <= candidate.exposed_port[0]
    assert route.points[1] == candidate.exposed_port
    assert _crosses_mark(route, actual)


def _render_explicit_suppress_case(directory, monkeypatch, *, shift=0, append=False):
    directory.mkdir()
    move = timedelta(days=shift)
    source = sr.with_calendar(sr.project({
        "source": sr.span("source", date(2027, 1, 4) + move, 2),
        "target": sr.span("target", date(2027, 2, 1) + move, 2),
        "blocker": sr.span("blocker", date(2027, 1, 5) + move, 2),
    }, [{"id": "link", "type": "dependency", "lag": "0d",
         "from": {"object": "source", "endpoint": "end"},
         "to": {"object": "target", "endpoint": "start"}}]))
    if append:
        source["objects"]["unrelated"] = sr.span("unrelated", date(2027, 1, 20) + move, 2)
    parts = sr.bundle()
    parts["view"]["body"]["rows"] = {"mode": "automatic"}
    parts["layout"]["relationRouting"] = {
        "search": "first-fit", "unroutable": "suppress", "maxBends": 4, "maxDetourRatio": 100,
    }
    compose = surface_composer.compose_surface_marks
    fixture_bounds = []

    def completed_blocker(base, **kwargs):
        batch = compose(base, **kwargs)
        fixture_bounds.append(base.timeline.bounds)
        return replace(batch, marks=tuple(
            replace(mark, bounds=base.timeline.bounds, corner_radius=0)
            if mark.source_ref == "blocker" else mark for mark in batch.marks))

    with monkeypatch.context() as patch:
        patch.setattr(surface_composer, "compose_surface_marks", completed_blocker)
        rendered = sr.render(directory, source, presentation=parts)
    return rendered, fixture_bounds[-1]


def test_default_preset_delta_anchors_and_route_class_survive_translation_and_unrelated_append(tmp_path):
    baseline = _render(tmp_path / "baseline")
    shifted = _render(tmp_path / "shifted", shift=7)
    appended = _render(tmp_path / "appended", append=True)
    for rendered in (baseline, shifted, appended):
        svg = ET.fromstring(rendered.artifact.content)
        content = "".join(svg.itertext())
        # The default counts the Thu→Sun interval as two working days (#1583).
        assert "+2d" in content and "-2d" in content
        assert not [item for item in rendered.scene.diagnostics if item.startswith("E_")]
    assert _anchor_sides(baseline) == _anchor_sides(shifted) == _anchor_sides(appended)
    assert _suppressed_relations(baseline) == _suppressed_relations(shifted) == _suppressed_relations(appended)


def test_explicit_calendar_day_comparison_retains_the_original_delta_text(tmp_path):
    rendered = _render(tmp_path / "calendar", delta_unit="calendar-days")
    content = "".join(ET.fromstring(rendered.artifact.content).itertext())
    assert "+3d" in content and "-2d" in content


@pytest.mark.parametrize("change", ["shift", "append"])
def test_previous_scene_keeps_revalidated_routes_and_delta_sides(tmp_path, change):
    # This seed must itself be a normal-stage route. The default extended
    # source finish overlaps the planned source endpoint and intentionally
    # starts in overlap recovery, which cannot be an accepted hint seed.
    source_finish = date(2027, 1, 13)
    target_actual_start = date(2027, 2, 5)
    baseline = _render(tmp_path / "baseline", source_actual_finish=source_finish,
                       target_actual_start=target_actual_start)
    assert not [item for item in baseline.info_diagnostics if isinstance(item, RelationResolutionInfo)]
    previous = tmp_path / "previous.scene.json"
    previous.write_bytes(serialize_scene(baseline.scene))
    kwargs = {"shift": 7} if change == "shift" else {"append": True}
    revised = _render(tmp_path / "revised", previous_scene=previous,
                       source_actual_finish=source_finish, target_actual_start=target_actual_start,
                       **kwargs)

    before_routes = _relation_routes(baseline)
    after_routes = _relation_routes(revised)
    receipts = [item for item in revised.info_diagnostics if isinstance(item, RelationHintReceipt)]
    accepted = {item.relation_id: item for item in receipts if item.disposition == "accepted"}
    assert accepted
    assert all(not item.searched for item in accepted.values())
    svg = ET.fromstring(revised.artifact.content)
    elements = {element.get("data-scene-id", element.get("id")): element for element in svg.iter()}
    for relation_id, receipt in accepted.items():
        current = next((route for route in after_routes.values() if route.scene_id == relation_id), None)
        assert current is not None, receipt
        key = (current.source_ref, current.from_instance_id, current.to_instance_id)
        assert key in before_routes, receipt
        prior = before_routes[key]
        assert len(current.points) == len(prior.points), receipt
        translation = (current.points[0][0] - prior.points[0][0],
                       current.points[0][1] - prior.points[0][1])
        if change == "shift":
            for old, new in zip(prior.points, current.points):
                assert new == pytest.approx((old[0] + translation[0], old[1] + translation[1]))
        else:
            # An appended row can move the target independently. Only the
            # endpoint-adjacent joins move; saved interior channels stay fixed.
            expected = list(prior.points)
            expected[0], expected[-1] = current.points[0], current.points[-1]
            if len(expected) > 2:
                x, y = expected[1]
                expected[1] = ((current.points[0][0], y) if prior.points[1][0] == prior.points[0][0]
                               else (x, current.points[0][1]))
                x, y = expected[-2]
                expected[-2] = ((current.points[-1][0], y) if prior.points[-2][0] == prior.points[-1][0]
                                else (x, current.points[-1][1]))
            assert current.points == tuple(expected)
        # The saved geometry is reanchored with changed marks. Its turns and
        # segments remain the same after removing that endpoint translation.
        if len(current.points) > 2:
            assert current.points[2:-2] == prior.points[2:-2], receipt
        assert tuple((b[0] == a[0], b[1] == a[1])
                     for a, b in zip(current.points, current.points[1:])) == tuple(
            (b[0] == a[0], b[1] == a[1])
            for a, b in zip(prior.points, prior.points[1:])), receipt
        assert current.scene_id in elements
        assert elements[current.scene_id].get("d")

    assert _anchor_sides(baseline) == _anchor_sides(revised)
    assert _suppressed_relations(baseline) == _suppressed_relations(revised)
    assert not [item for item in revised.info_diagnostics if isinstance(item, RelationResolutionInfo)]


@pytest.mark.parametrize(("change", "disposition"), [("shift", "accepted"), ("append", "invalidated")])
def test_previous_scene_revalidates_connected_actual_endpoint_corridor(tmp_path, change, disposition):
    # The actual source mark overlaps the planned endpoint. The route leaves
    # through their named connected comparison-host corridor in NORMAL.
    baseline = _render(tmp_path / "baseline")
    route, = _relation_routes(baseline).values()
    _assert_connected_actual_endpoint_corridor(baseline)
    assert not [item for item in baseline.info_diagnostics if isinstance(item, RelationResolutionInfo)]

    previous = tmp_path / "previous.scene.json"
    previous.write_bytes(serialize_scene(baseline.scene))
    kwargs = {"shift": 7} if change == "shift" else {"append": True}
    revised = _render(tmp_path / "revised", previous_scene=previous, **kwargs)
    receipt, = [item for item in revised.info_diagnostics
                if isinstance(item, RelationHintReceipt) and item.relation_id == route.scene_id]
    assert receipt.disposition == disposition
    assert receipt.reason == ("revalidated" if disposition == "accepted" else "E_LAYOUT_ROUTE_THROUGH_MARK")
    _assert_connected_actual_endpoint_corridor(revised)
    assert not [item for item in revised.info_diagnostics if isinstance(item, RelationResolutionInfo)]


def test_explicit_suppression_identity_survives_uniform_shift_and_unrelated_append(tmp_path, monkeypatch):
    cases = (
        _render_explicit_suppress_case(tmp_path / "baseline", monkeypatch),
        _render_explicit_suppress_case(tmp_path / "shifted", monkeypatch, shift=7),
        _render_explicit_suppress_case(tmp_path / "appended", monkeypatch, append=True),
    )
    identities = []
    for rendered, bounds in cases:
        blocker, = [item for item in rendered.surface.primitives
                    if item.source_ref == "blocker" and item.kind.value == "Rect"]
        assert blocker.bounds == tuple(float(value) for value in (
            bounds.inline, bounds.block, bounds.inline_size, bounds.block_size))
        svg = ET.fromstring(rendered.artifact.content)
        elements = {element.get("data-scene-id", element.get("id")): element for element in svg.iter()}
        assert blocker.scene_id in elements
        assert float(elements[blocker.scene_id].get("width")) == pytest.approx(blocker.bounds[2])
        assert float(elements[blocker.scene_id].get("height")) == pytest.approx(blocker.bounds[3])
        warnings = _suppressed_relations(rendered)
        assert warnings  # Non-vacuous witness; compare route identities, not summary/count payloads.
        assert not [item for item in rendered.scene.diagnostics if item.startswith("E_")]
        identities.append({warning.split(":", 1)[1] for warning in warnings})
    assert identities[0] == identities[1] == identities[2]


def test_unrelated_relation_order_preserves_completed_routes_and_svg(tmp_path):
    source = sr.with_calendar(sr.chain_project(groups=2, per_group=2))
    parts = sr.bundle()
    parts["view"]["body"]["rows"] = {"mode": "automatic"}
    parts["view"]["body"]["visibility"]["relations"] = "all"
    parts["layout"]["relationRouting"] = {
        "search": "first-fit", "unroutable": "suppress",
        "maxBends": 4, "maxDetourRatio": 100,
    }
    evidence = []
    for name, relations in (("forward", source["relations"]),
                            ("reverse", list(reversed(source["relations"])))):
        directory = tmp_path / name
        directory.mkdir()
        rendered = sr.render(directory, {**source, "relations": relations}, presentation=parts)
        paths = {(item.from_instance_id, item.to_instance_id): item
                 for item in rendered.surface.primitives if item.source_kind == "relation"}
        assert len(paths) == 2  # Both unrelated dependencies are genuinely drawn.
        assert all(source_id and target_id for source_id, target_id in paths)
        assert not _suppressed_relations(rendered)
        assert not [item for item in rendered.scene.diagnostics if item.startswith("E_")]
        svg = ET.fromstring(rendered.artifact.content)
        elements = {element.get("data-scene-id", element.get("id")): element for element in svg.iter()}
        assert {item.scene_id for item in paths.values()} <= elements.keys()
        assert all(elements[item.scene_id].get("d") for item in paths.values())
        # Array-position resource identities can differ; compare completed geometry
        # and the adapter's actual path commands by stable endpoint instances.
        evidence.append({key: (item.points, item.path_commands,
                               elements[item.scene_id].get("d")) for key, item in paths.items()})
    assert evidence[0] == evidence[1]
