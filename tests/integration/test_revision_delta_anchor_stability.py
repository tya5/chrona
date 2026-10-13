"""#1300: actual Scene/SVG revision evidence from project-independent fixtures."""
from datetime import date, timedelta
from dataclasses import replace
import xml.etree.ElementTree as ET
import yaml
import pytest

from chrona.presentation.layout import surface_composer
from chrona.presentation.model.info_diagnostics import RelationHintReceipt
from chrona.presentation.scene.serialization import serialize_scene
from chrona.usecases.draft_render import DraftRenderRequest, render_draft
from tests.support import synthetic_review as sr


def _render(directory, *, shift=0, append=False, previous_scene=None):
    directory.mkdir()
    move = timedelta(days=shift)
    source = sr.with_calendar(sr.project({
        "source": sr.span("source", date(2027, 1, 4) + move, 10),
        "target": sr.span("target", date(2027, 2, 1) + move, 10),
    }, [{"id": "source-target", "type": "dependency", "lag": "0d",
         "from": {"object": "source", "endpoint": "end"},
         "to": {"object": "target", "endpoint": "start"}}]))
    if append:
        source["objects"]["unrelated"] = sr.span("unrelated", date(2027, 1, 20), 5)
    actual = {"version": "chrona/actual-set/v0.3", "kind": "actual-set", "id": "actuals", "body": {
        "asOf": (date(2027, 2, 20) + move).isoformat(), "observations": [
            {"id": "source-done", "sequence": 1, "projectObjectId": "source", "actual": {
                "start": (date(2027, 1, 4) + move).isoformat(),
                "finish": (date(2027, 1, 17) + move).isoformat(), "progress": 1}},
            {"id": "target-done", "sequence": 1, "projectObjectId": "target", "actual": {
                "start": (date(2027, 2, 1) + move).isoformat(),
                "finish": (date(2027, 2, 9) + move).isoformat(), "progress": 1}},
        ]}}
    project_path, actual_path = directory / "project.yaml", directory / "actual.yaml"
    project_path.write_text(yaml.safe_dump(source, sort_keys=False), encoding="utf-8")
    actual_path.write_text(yaml.safe_dump(actual, sort_keys=False), encoding="utf-8")
    return render_draft(DraftRenderRequest(project_path, "svg", actual=actual_path,
                                           previous_scene=previous_scene)).rendered


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
        assert "+3d" in content and "-2d" in content
        assert not [item for item in rendered.scene.diagnostics if item.startswith("E_")]
    assert _anchor_sides(baseline) == _anchor_sides(shifted) == _anchor_sides(appended)
    assert _suppressed_relations(baseline) == _suppressed_relations(shifted) == _suppressed_relations(appended)


@pytest.mark.parametrize("change", ["shift", "append"])
def test_previous_scene_keeps_revalidated_routes_and_delta_sides(tmp_path, change):
    baseline = _render(tmp_path / "baseline")
    previous = tmp_path / "previous.scene.json"
    previous.write_bytes(serialize_scene(baseline.scene))
    kwargs = {"shift": 7} if change == "shift" else {"append": True}
    revised = _render(tmp_path / "revised", previous_scene=previous, **kwargs)

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
        assert current.points[-1] == pytest.approx((prior.points[-1][0] + translation[0],
                                                    prior.points[-1][1] + translation[1]))
        for old, new in zip(prior.points, current.points):
            assert new == pytest.approx((old[0] + translation[0], old[1] + translation[1]))
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
