"""First-run lane order/count policy through actual packaged Draft/Scene/SVG."""
from datetime import date
from xml.etree import ElementTree

import pytest
import yaml

from chrona.resources import builtin_preset_library_resource
from chrona.presentation.contracts import ClosureIdentity, ContractError, parse_contract
from chrona.usecases.draft_render import DraftRenderRequest, render_draft
from tests.support import synthetic_review as sr


_ENTRIES = yaml.safe_load(builtin_preset_library_resource().read_text())["entries"]
PRESETS = [entry["id"] for entry in _ENTRIES]
DESIGN_PRESETS = {entry["id"] for entry in _ENTRIES if entry["members"]["layout"]["sourceRoot"].startswith("designs/")}
# Group header rows need a grouping, and no generic grouping keeps one global start order (named gap 8 in
# docs/diagnostics/muted-executive-vocabulary-gaps.md); start order holds within each group.
DESIGN_PRESETS |= {"muted-executive"}


@pytest.mark.parametrize("policy", [False, True, "auto", "omitted"])
def test_lane_count_ingress_preserves_boolean_auto_and_absence(policy):
    view = sr.bundle("executive-light")["view"]
    if policy == "omitted":
        view["body"]["rows"]["laneTable"].pop("count")
    else:
        view["body"]["rows"]["laneTable"]["count"] = policy
    parsed = parse_contract(ClosureIdentity("view", view["id"], "r", "sha256:" + "a" * 64), view)
    assert parsed.view.rows.lane_table.count == (False if policy == "omitted" else policy)


@pytest.mark.parametrize("policy", [None, 1, "false", "always"])
def test_lane_count_ingress_rejects_other_values(policy):
    view = sr.bundle("executive-light")["view"]
    view["body"]["rows"]["laneTable"]["count"] = policy
    with pytest.raises(ContractError):
        parse_contract(ClosureIdentity("view", view["id"], "r", "sha256:" + "a" * 64), view)


@pytest.mark.parametrize("preset", PRESETS)
def test_every_builtin_preset_shows_start_order_without_singleton_items_column(tmp_path, preset):
    source = sr.project({
        "zeta-kickoff": sr.point("zeta-kickoff", date(2027, 1, 4), title="Kickoff"),
        "mid-build": sr.span("mid-build", date(2027, 1, 11), 40, title="Build"),
        "alpha-launch": sr.point("alpha-launch", date(2027, 3, 1), title="Launch"),
    })
    source["project"] = {"id": "order", "title": "Row order"}
    source.pop("entities")
    for item in source["objects"].values():
        item.pop("fields")
    path = tmp_path / "order.yaml"
    path.write_text(yaml.safe_dump(source, sort_keys=False), encoding="utf-8")
    rendered = render_draft(DraftRenderRequest(project=path, preset=preset, target_kind="svg")).rendered
    columns = [item.text for item in rendered.surface.primitives if item.purpose == "table-column-label"]
    assert "Items" not in columns
    titles = [item for item in rendered.surface.primitives
              if item.purpose == "table-cell" and item.scene_id.endswith((":Task", ":Lane"))]
    member_by_row = {member.row_id: member.member_id for member in rendered.surface.lane_members}
    order = [member_by_row.get(item.source_ref, item.source_ref) for item in titles]
    if preset in DESIGN_PRESETS:
        # A packaged design groups by object type for its group headers (#429): start order holds within each group.
        assert sorted(order) == ["alpha-launch", "mid-build", "zeta-kickoff"]
        assert order.index("zeta-kickoff") < order.index("alpha-launch")
    else:
        assert order == ["zeta-kickoff", "mid-build", "alpha-launch"]
    assert all(item.text for item in titles)
    ids = [item.scene_id for item in titles]
    svg = ElementTree.fromstring(rendered.artifact.content)
    serialized = [element.get("data-scene-id", element.get("id")) for element in svg.iter()]
    assert [identifier for identifier in serialized if identifier in ids] == ids
