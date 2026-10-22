from decimal import Decimal

import pytest

from chrona.presentation.layout.group_header_fit import (
    GroupHeaderFit, GroupHeaderFitPlan, GroupHeaderInlineDemand,
    GroupHeaderOwnerInlineDemand,
)


def test_horizontal_demotion_reports_source_inline_demand_for_indivisible_unit():
    plan = GroupHeaderFitPlan(
        groups=(GroupHeaderFit(
            "team-a", "UNBREAKABLE", 240.0, ("UNBREAKABLE",), 20.0,
            Decimal("170.4"), horizontal_fits=False, uses_vertical_tag=True,
        ),),
        header_inline_start=130.0,
        header_inline_size=119.2,
        minimum_header_block_size=20.0,
        source_inline_prefix=Decimal("30.8"),
    )

    with pytest.raises(GroupHeaderInlineDemand) as caught:
        plan.demote(frozenset({"team-a"}))

    assert caught.value.group_id == "team-a"
    assert caught.value.label == "UNBREAKABLE"
    assert caught.value.minimum_source_inline == Decimal("201.2")
    assert caught.value.available_source_inline == Decimal("150.0")


def test_still_fitting_vertical_preference_does_not_request_inline_growth():
    plan = GroupHeaderFitPlan(
        groups=(GroupHeaderFit(
            "team-a", "A", 10.0, ("A",), 20.0,
            Decimal("5.0"), horizontal_fits=False, uses_vertical_tag=True,
        ),),
        header_inline_start=130.0,
        header_inline_size=119.2,
        minimum_header_block_size=20.0,
        source_inline_prefix=Decimal("30.8"),
    )

    retained = plan.demote(frozenset())
    assert retained.group("team-a").uses_vertical_tag


def test_vertical_fit_uses_actual_tab_inset_cell_and_demotes_before_rows_close():
    plan = GroupHeaderFitPlan(
        groups=(
            GroupHeaderFit("short-a", "Ana", 19.6665, ("Ana",), 20.0,
                           Decimal("20"), horizontal_fits=True, uses_vertical_tag=True),
            GroupHeaderFit("short-b", "Ben", 19.9815, ("Ben",), 20.0,
                           Decimal("20"), horizontal_fits=True, uses_vertical_tag=True),
            GroupHeaderFit("fits", "Team", 19.0, ("Team",), 20.0,
                           Decimal("20"), horizontal_fits=True, uses_vertical_tag=True),
        ),
        header_inline_start=63.0,
        header_inline_size=300.0,
        minimum_header_block_size=20.0,
        vertical_tag_block_inset=6.0,
    )
    spans = {"short-a": 20.13125, "short-b": 20.13125, "fits": 25.0}

    # Both short groups pass a raw span-vs-required comparison but their actual
    # tag cells lose 6px to the declared top/bottom tab gap.
    assert spans["short-a"] > plan.group("short-a").vertical_required_block
    assert spans["short-b"] > plan.group("short-b").vertical_required_block
    assert plan.vertical_tags_missing_full_fit(spans) == frozenset({"short-a", "short-b"})
    closed = plan.demote(plan.vertical_tags_missing_full_fit(spans))
    assert not closed.group("short-a").uses_vertical_tag
    assert not closed.group("short-b").uses_vertical_tag
    assert closed.group("fits").uses_vertical_tag
    assert dict(closed.header_sizes) == {"short-a": 20.0, "short-b": 20.0}

    # A label that exactly fits the actual tab cell remains vertical.
    exact = {
        "short-a": 19.6665 + plan.vertical_tag_block_inset,
        "short-b": 19.9815 + plan.vertical_tag_block_inset,
        "fits": 19.0 + plan.vertical_tag_block_inset,
    }
    assert plan.vertical_tags_missing_full_fit(exact) == frozenset()


def test_tab_only_indivisible_header_requests_its_shared_outer_owner_floor():
    plan = GroupHeaderFitPlan(
        groups=(GroupHeaderFit(
            "team-a", "UNBREAKABLE", 10.0, ("UNBREAKABLE",), 20.0,
            Decimal("170.4"), horizontal_fits=False, uses_vertical_tag=False,
        ),),
        header_inline_start=130.0,
        header_inline_size=119.2,
        minimum_header_block_size=20.0,
        source_inline_demand=False,
        vertical_tag_plan=False,
    )

    with pytest.raises(GroupHeaderOwnerInlineDemand) as caught:
        plan.require_owner_horizontal_room(
            owner_node_id="main", available_owner_inline=Decimal("640"))

    assert caught.value.group_id == "team-a"
    assert caught.value.owner_node_id == "main"
    assert caught.value.minimum_owner_inline == Decimal("691.2")
    assert caught.value.available_owner_inline == Decimal("640")
