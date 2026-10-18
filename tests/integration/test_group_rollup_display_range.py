"""Native evidence that rollup Plan cells close over child points (#1701 row 1)."""
from datetime import date
from xml.etree import ElementTree

from chrona.scheduling.scheduler import ReferenceScheduler
from tests.support import synthetic_review as sr


def _project():
    objects = {
        "design": {"type": "group", "title": "Design", "schedule": {"mode": "rollup"}},
        # Core span endpoints are half-open: this span ends on March 6 exclusively.
        "implementation": {**sr.span("implementation", date(2027, 3, 1), 5), "parent": "design"},
        "signoff": {**sr.point("signoff", date(2027, 3, 6), title="Design sign-off"), "parent": "design"},
        "follow-up": sr.span("follow-up", date(2027, 3, 8), 2),
    }
    relation = {"id": "design-to-follow-up", "type": "dependency", "lag": "0d",
                "from": {"object": "design", "endpoint": "end"},
                "to": {"object": "follow-up", "endpoint": "start"}}
    return sr.project(objects, (relation,))


def test_group_plan_range_includes_child_gate_without_changing_core_endpoints(tmp_path):
    source = _project()
    scheduled = ReferenceScheduler().schedule(source)
    assert not scheduled.diagnostics
    assert scheduled.placements["design"] == {
        "start": date(2027, 3, 1), "end": date(2027, 3, 6),
    }
    assert scheduled.placements["follow-up"]["start"] == date(2027, 3, 8)
    relation = source["relations"][0]
    assert relation["from"] == {"object": "design", "endpoint": "end"}
    assert relation["to"] == {"object": "follow-up", "endpoint": "start"}

    parts = sr.bundle("executive-light")
    parts["view"]["body"]["selection"]["exclude"] = {"objectTypes": []}
    parts["view"]["body"]["rows"] = {"mode": "automatic"}
    parts["view"]["body"]["grouping"] = {
        "by": "hierarchy", "depth": "all", "rollup": "header", "presentation": "header",
    }
    parts["view"]["body"]["tableColumns"] = [{
        "id": "Plan", "source": {"facet": "planned"}, "format": "dateRange",
        "endDisplay": "inclusive", "missing": "blank", "align": "start", "width": "content",
        "headerOrientation": "horizontal",
    }]
    parts["view"]["body"]["hierarchyColumn"] = "Plan"
    rendered = sr.render(tmp_path, source, presentation=parts)

    group_plan = next(item for item in rendered.surface.primitives
                      if item.scene_id == "cell:design:Plan")
    assert group_plan.text == "01 Mar – 06 Mar"
    gate_plan = next(item for item in rendered.surface.primitives
                     if item.scene_id == "cell:signoff:Plan")
    assert gate_plan.text == "06 Mar 2027"

    # The cell is user-visible in the SVG, while the scheduler-owned endpoint and
    # the dependency's typed ports remain at March 6 -> March 8.
    svg = ElementTree.fromstring(rendered.artifact.content)
    text_by_id = {node.attrib.get("data-scene-id"): "".join(node.itertext()) for node in svg.iter()
                  if node.attrib.get("data-scene-id")}
    assert text_by_id["cell:design:Plan"] == "01 Mar – 06 Mar"
    assert scheduled.placements["design"]["end"] == date(2027, 3, 6)
    assert scheduled.placements["follow-up"]["start"] == date(2027, 3, 8)
    assert ReferenceScheduler().schedule(source).placements == scheduled.placements
    assert source["relations"][0]["from"] == {"object": "design", "endpoint": "end"}
    assert source["relations"][0]["to"] == {"object": "follow-up", "endpoint": "start"}
