"""A measured group-name minimum re-enters ordinary source sizing before routing (#1906)."""
from decimal import Decimal
import xml.etree.ElementTree as ET

import pytest

from chrona.presentation.layout import surface_render_plan, surface_source_closure
from chrona.presentation.layout.group_header_fit import GroupHeaderInlineDemand, GroupHeaderOwnerInlineDemand
from chrona.usecases import render_review as render_review_module
from chrona.usecases.render_review import RenderFailed
from tests.support import synthetic_review as sr
from tests.support import text_treatments as tt


def _unbounded_vertical_parts():
    parts = sr.bundle("control-room-dark")
    tt.with_vertical_groups(parts, size=22)
    # The packaged profile intentionally caps the table at 40% of the source.
    # These cases exercise an uncapped source and the explicit-cap refusal separately.
    sr.find_node(parts["layout"], "table").pop("maxInlineShare", None)
    return parts


def _set_group_label(project, label):
    project["entities"]["team-0"]["title"] = label


def _group_header_text(rendered):
    return next(item for item in rendered.surface.primitives
                if item.scene_id == "group-header:team-0"
                or item.scene_id.startswith("group-tag:team-0:"))


@pytest.mark.parametrize("demand_at", [1, 2], ids=["natural-candidate", "final-pre-route-closure"])
def test_new_group_floor_is_present_on_retried_candidate_before_pre_route_geometry(
        tmp_path, monkeypatch, demand_at):
    project = sr.bunched_project(groups=1, per_group=1)
    parts = sr.bundle("control-room-dark")
    tt.with_vertical_groups(parts, size=22)
    floor = Decimal(500)
    original = surface_render_plan.prepare_surface_natural_candidate
    original_prepare = surface_source_closure.prepare_surface_render_plan
    plans = []

    def prepare_plan(value, **kwargs):
        plan_state = {"observed": [], "demand_raised": False}
        plans.append(plan_state)
        return original_prepare(value, **kwargs)

    def require_once(request):
        table_measurement = request.measured_sources.measurements["table"]
        table_input = request.measured_sources.inputs["table"]
        table = next(item for item in request.layout_manifest.decisions if item.node_id == "table")
        plan_state = plans[-1]
        observed = plan_state["observed"]
        observed.append((table_measurement.min_inline, table_input.min_inline, table.bounds.inline_size))
        if len(observed) == demand_at and not plan_state["demand_raised"]:
            plan_state["demand_raised"] = True
            raise GroupHeaderInlineDemand(
                group_id="identity-40", label="UNBREAKABLE-ID", minimum_source_inline=floor,
                available_source_inline=Decimal(300))
        if len(observed) > demand_at:
            assert table_measurement.min_inline >= floor
            assert table_input.min_inline >= floor
        return original(request)

    monkeypatch.setattr(surface_source_closure, "prepare_surface_render_plan", prepare_plan)
    monkeypatch.setattr(render_review_module, "prepare_surface_render_plan", prepare_plan)
    monkeypatch.setattr(surface_render_plan, "prepare_surface_natural_candidate", require_once)

    rendered = sr.render(tmp_path, project, presentation=parts, viewport=(1600, 900))

    assert plans
    assert all(plan["demand_raised"] for plan in plans)
    for plan in plans:
        observed = plan["observed"]
        assert len(observed) > demand_at
        assert observed[0][0] < floor
        assert observed[0][2] < floor
        assert all(measurement >= floor and source_input >= floor
                   for measurement, source_input, _ in observed[demand_at:])
    table = next(slot for slot in rendered.surface.slots if slot.slot_id == "table")
    assert Decimal(str(table.bounds[2])) >= floor


def test_unbreakable_vertical_group_name_grows_source_and_is_visible_in_svg(tmp_path):
    label = "IDENTITY_" * 40
    project = sr.bunched_project(groups=1, per_group=1)
    _set_group_label(project, label)

    rendered = sr.render(tmp_path, project, presentation=_unbounded_vertical_parts(), viewport=(1600, None))

    header = _group_header_text(rendered)
    assert header.text == label
    assert len(header.text_layout.lines) == 1
    table = next(slot for slot in rendered.surface.slots if slot.slot_id == "table")
    assert Decimal(str(table.bounds[2])) >= Decimal(str(header.bounds[0] + header.bounds[2] - table.bounds[0]))
    svg = ET.fromstring(rendered.artifact.content)
    text = next(node for node in svg.iter()
                if node.tag.rsplit("}", 1)[-1] == "text"
                and node.attrib.get("data-scene-id") == header.scene_id)
    visible = "".join(text.itertext())
    assert label in visible
    assert "…" not in visible and "..." not in visible
    growth = [warning for warning in rendered.surface.fit_warnings
              if warning.placement_id == "group-header:team-0"]
    assert len(growth) == 1
    assert growth[0].code == "W_LAYOUT_VISIBLE_OVERFLOW"
    assert growth[0].failure_kind == "group-header-unbreakable-inline"
    assert growth[0].behaviour == "grow-owner-inline"
    assert growth[0].subjects[0].source_ref == "team-0"


def test_fitting_vertical_group_tag_does_not_inflate_source_inline_width(tmp_path):
    project = sr.bunched_project(groups=1, per_group=1)
    _set_group_label(project, "Ops")
    parts = _unbounded_vertical_parts()

    rendered = sr.render(tmp_path, project, presentation=parts, viewport=(1600, None))

    table = next(slot for slot in rendered.surface.slots if slot.slot_id == "table")
    header = next(item for item in rendered.surface.primitives
                  if item.scene_id.startswith("group-tag:team-0:"))
    assert header.text == "Ops"
    horizontal_parts = sr.bundle("control-room-dark")
    tt.with_vertical_groups(horizontal_parts, size=22, mode="horizontal")
    sr.find_node(horizontal_parts["layout"], "table").pop("maxInlineShare", None)
    horizontal_dir = tmp_path / "horizontal"
    horizontal_dir.mkdir()
    horizontal = sr.render(horizontal_dir, project, presentation=horizontal_parts, viewport=(1600, None))
    horizontal_table = next(slot for slot in horizontal.surface.slots if slot.slot_id == "table")
    assert table.bounds[2] == horizontal_table.bounds[2]


def test_authored_table_share_cap_rejects_unbreakable_group_name_with_cause(tmp_path):
    label = "IDENTITY_" * 40
    project = sr.bunched_project(groups=1, per_group=1)
    _set_group_label(project, label)
    parts = sr.bundle("control-room-dark")
    tt.with_vertical_groups(parts, size=22)

    with pytest.raises(RenderFailed) as caught:
        sr.render(tmp_path, project, presentation=parts, viewport=(1600, None))

    error = caught.value
    assert error.code == "E_LAYOUT_TABLE_OVERFLOW"
    assert error.source_ref == "/layout/groupHeaders/team-0"


def test_shared_group_header_owner_floor_grows_root_before_retry(tmp_path, monkeypatch):
    project = sr.bunched_project(groups=1, per_group=1)
    parts = sr.bundle("control-room-dark")
    tt.with_vertical_groups(parts, size=22)
    original = surface_render_plan.prepare_surface_natural_candidate
    original_prepare = surface_source_closure.prepare_surface_render_plan
    plans = []

    def prepare_plan(value, **kwargs):
        plan_state = {"observed": [], "demand_raised": False}
        plans.append(plan_state)
        return original_prepare(value, **kwargs)

    def require_owner_once(request):
        owner = next(item for item in request.layout_manifest.decisions if item.node_id == "review")
        plan_state = plans[-1]
        observed = plan_state["observed"]
        observed.append(owner.bounds.inline_size)
        if not plan_state["demand_raised"]:
            plan_state["demand_raised"] = True
            available = owner.bounds.inline_size
            raise GroupHeaderOwnerInlineDemand(
                group_id="team-0", label="Synthetic full group name", owner_node_id="review",
                minimum_owner_inline=available + Decimal(500), available_owner_inline=available)
        return original(request)

    monkeypatch.setattr(surface_source_closure, "prepare_surface_render_plan", prepare_plan)
    monkeypatch.setattr(render_review_module, "prepare_surface_render_plan", prepare_plan)
    monkeypatch.setattr(surface_render_plan, "prepare_surface_natural_candidate", require_owner_once)

    rendered = sr.render(tmp_path, project, presentation=parts, viewport=(1600, 900))

    assert plans
    assert all(plan["demand_raised"] for plan in plans)
    for plan in plans:
        observed = plan["observed"]
        assert len(observed) > 1
        assert observed[1] >= observed[0] + 500
    review = next(slot for slot in rendered.surface.slots if slot.slot_id == "review-surface")
    assert Decimal(str(review.bounds[2])) >= observed[1]
    warning = next(item for item in rendered.surface.fit_warnings
                    if item.placement_id == "group-header:team-0")
    assert warning.failure_kind == "group-header-unbreakable-inline"
    assert warning.behaviour == "grow-owner-inline"
    assert warning.required_inline == observed[1]
