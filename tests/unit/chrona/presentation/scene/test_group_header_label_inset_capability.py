"""Closed Theme capability coverage for the horizontal group-header inset (#1284)."""

from chrona.presentation.scene.capabilities import (
    theme_role_contract,
    theme_role_property_consumer,
)


def test_group_header_admits_only_its_selected_layout_inset_measurement():
    contract = theme_role_contract("groupHeader")

    assert contract is not None
    assert "labelInset" in contract.properties
    assert theme_role_property_consumer("groupHeader", "labelInset") == contract.consumer

    # These are axis-tier measurements, not generic text-role properties.
    for property_name in ("labelGap", "laneBlockSize"):
        assert property_name not in contract.properties
        assert theme_role_property_consumer("groupHeader", property_name) is None

    # The existing axis owner still admits both properties.
    for property_name in ("labelGap", "laneBlockSize"):
        assert theme_role_property_consumer("axis", property_name) is not None
