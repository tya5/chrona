import pytest

from chrona.presentation.model.point_paint import resolve_point_paint_role


@pytest.mark.parametrize("role", (
    "planned", "actual", "snapshot", "scenario", "missing-actual",
    "milestone", "custom-point-role",
))
@pytest.mark.parametrize("gate_declared", (False, True))
@pytest.mark.parametrize("legend", (False, True))
def test_gate_role_substitution_preserves_only_the_existing_point_and_legend_cases(
    role, gate_declared, legend,
):
    if legend and role == "milestone":
        expected = "gate" if gate_declared else "planned"  # the key is a miniature of the chart's planned point (#499)
    elif gate_declared and not legend and role == "planned":
        expected = "gate"
    else:
        expected = role

    assert resolve_point_paint_role(role, gate_declared=gate_declared, legend=legend) == expected
