"""Hint-first revision stability with an unrelated moving primary mark (#1754)."""
from datetime import date

import pytest
import yaml

from chrona.presentation.model.info_diagnostics import (
    RelationHintReceipt,
    RelationResolutionInfo,
)
from chrona.presentation.scene.serialization import serialize_scene
from chrona.resources import default_preset_resource, default_preset_root
from chrona.usecases.draft_render import DraftRenderRequest, render_draft
from tests.support import synthetic_review as sr


def _inputs(search_policy):
    parts = sr.bundle()
    view = parts["view"]
    body = view["body"]
    for name in ("selection", "grouping", "ordering"):
        body.pop(name, None)
    body["rows"] = {"mode": "explicit", "items": [
        {"id": f"{object_id}-row", "label": title, "depth": 0,
         "tableSubject": object_id,
         "items": [{"id": object_id,
                    "source": {"kind": "primary", "object": object_id},
                    "track": "stacked"}]}
        for object_id, title in (("source", "Source"), ("blocker", "Blocker"), ("target", "Target"))
    ]}
    body["window"] = {"mode": "explicit", "start": "2027-01-01", "end": "2027-02-15"}
    body["visibility"] = {"labels": False, "relations": "semantic", "annotations": "none"}
    preset = yaml.safe_load(default_preset_resource().read_bytes())
    layout = yaml.safe_load((default_preset_root() / preset["body"]["resources"]["layout"]["path"])
                            .read_bytes())
    layout["relationRouting"] = {
        "search": search_policy, "unroutable": "relax", "maxBends": 4, "maxDetourRatio": 100,
    }
    return parts, layout


def _project(blocker_start):
    return sr.with_calendar(sr.project({
        "source": sr.span("source", date(2027, 1, 3), 5),
        "blocker": sr.span("blocker", blocker_start, 3),
        "target": sr.span("target", date(2027, 2, 2), 5),
    }, [{"id": "source-target", "type": "dependency",
         "from": {"object": "source", "endpoint": "end"},
         "to": {"object": "target", "endpoint": "start"}}]))


def _render(directory, project, parts, layout, previous_scene=None):
    directory.mkdir()
    project_path = directory / "project.yaml"
    project_path.write_text(yaml.safe_dump(project, sort_keys=False), encoding="utf-8")
    view_path = sr._write(directory / "view.yaml", parts["view"])
    theme_path = sr._write(directory / "theme.yaml", parts["theme"])
    scheme_path = sr._write(directory / "scheme.yaml", parts["scheme"])
    layout_path = sr._write(directory / "layout.yaml", layout)
    return render_draft(DraftRenderRequest(project_path, "svg", view=view_path,
        theme=theme_path, scheme=scheme_path, layout=layout_path,
        previous_scene=previous_scene)).rendered


def _relation(rendered):
    route, = [item for item in rendered.surface.primitives
              if item.kind.value == "Path" and item.source_kind == "relation"]
    return route


def _mark(rendered, object_id):
    mark, = [item for item in rendered.surface.primitives
             if item.source_ref == object_id and item.scene_id.startswith("planned:")]
    return mark


@pytest.mark.parametrize("search_policy", ("first-fit", "best"))
def test_unrelated_slip_keeps_valid_corridor_and_moved_primary_mark_gets_safe_detour(
        tmp_path, search_policy):
    parts, layout = _inputs(search_policy)
    baseline = _render(tmp_path / "baseline", _project(date(2027, 1, 30)), parts, layout)
    prior = tmp_path / "prior.scene.json"
    prior.write_bytes(serialize_scene(baseline.scene))
    old_route = _relation(baseline)
    old_source = _mark(baseline, "source")
    old_target = _mark(baseline, "target")

    # The blocker moves, but remains clear of the saved corridor. The endpoint
    # marks and the complete prior path should therefore be retained.
    clear_slip = _render(tmp_path / "clear-slip", _project(date(2027, 1, 31)),
                         parts, layout, prior)
    clear_route = _relation(clear_slip)
    clear_receipts = [item for item in clear_slip.info_diagnostics
                      if isinstance(item, RelationHintReceipt)]
    clear_receipt, = [item for item in clear_receipts if item.relation_id == old_route.scene_id]
    assert clear_receipt.disposition == "accepted"
    assert clear_route.points == old_route.points
    assert _mark(clear_slip, "source").bounds == old_source.bounds
    assert _mark(clear_slip, "target").bounds == old_target.bounds

    # Move the blocker one day earlier into the saved vertical corridor. Its
    # row and both relation endpoints stay fixed, so only ordinary NORMAL-
    # domain search can accept a replacement before RELAX removes mark obstacles.
    blocked_slip = _render(tmp_path / "blocked-slip", _project(date(2027, 1, 29)),
                          parts, layout, prior)
    route = _relation(blocked_slip)
    blocker = _mark(blocked_slip, "blocker")

    left, top, width, height = blocker.bounds
    rect = (left, top, left + width, top + height)
    def crosses(points):
        for first, second in zip(points, points[1:]):
            x1, y1 = first
            x2, y2 = second
            if x1 == x2 and rect[0] < x1 < rect[2] and max(min(y1, y2), rect[1]) < min(max(y1, y2), rect[3]):
                return True
            if y1 == y2 and rect[1] < y1 < rect[3] and max(min(x1, x2), rect[0]) < min(max(x1, x2), rect[2]):
                return True
        return False

    receipts = [item for item in blocked_slip.info_diagnostics
                if isinstance(item, RelationHintReceipt)]
    receipt, = [item for item in receipts if item.relation_id == old_route.scene_id]
    if search_policy == "best":
        # Best's original corridor is already clear of this moved blocker;
        # the saved geometry remains admissible and needs no detour.
        assert not crosses(old_route.points)
        assert not crosses(route.points)
        assert receipt.disposition == "accepted"
        assert route.points == old_route.points
        assert not [item for item in blocked_slip.info_diagnostics
                    if isinstance(item, RelationResolutionInfo)
                    and item.relation_id == old_route.scene_id]
    else:
        # First-fit's saved corridor intersects the moved blocker, so it must
        # be invalidated and replaced by a clear route.
        assert crosses(old_route.points)
        assert not crosses(route.points)
        assert receipt.disposition == "invalidated"
        assert receipt.reason == "E_LAYOUT_ROUTE_THROUGH_MARK"
        assert route.points != old_route.points
        assert not [item for item in blocked_slip.info_diagnostics
                    if isinstance(item, RelationResolutionInfo)
                    and item.relation_id == old_route.scene_id]
    assert not any(item.startswith(("E_SCENE_RELATION_THROUGH_MARK", "W_SCENE_RELATION_THROUGH_MARK"))
                   for item in blocked_slip.scene.diagnostics)
    assert _mark(blocked_slip, "source").bounds == old_source.bounds
    assert _mark(blocked_slip, "target").bounds == old_target.bounds
