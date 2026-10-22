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
