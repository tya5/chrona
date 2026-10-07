"""Physical mark radii make the legacy ratio optional only when explicitly overridden (#1198)."""
from decimal import Decimal

import pytest

from chrona.presentation.model.theme_tokens import ThemeTokenError, ThemeTokenView
from tests.unit.chrona.presentation.model.test_theme_tokens import _mark_theme


def _physical_only(*, value=3):
    theme = _mark_theme()
    body = theme["body"]
    body["values"]["physical-radius"] = {"type": "radius", "value": value}
    planned = body["roles"]["planned"]
    planned.pop("markCornerRadius")
    planned["cornerRadius"] = "physical-radius"
    return theme


def test_physical_only_binding_satisfies_mark_geometry_without_legacy_placeholder():
    geometry = ThemeTokenView(_physical_only()).mark_geometry("planned")
    assert geometry[:3] == (Decimal("0.25"), Decimal("0.125"), 10)


def test_physical_zero_is_present_and_does_not_fall_back_to_a_legacy_binding():
    geometry = ThemeTokenView(_physical_only(value=0)).mark_geometry("planned")
    assert geometry[3] == Decimal(0)


@pytest.mark.parametrize("ratio", ["0", "0.2", "0.5"])
def test_legacy_only_ratio_is_retained_exactly(ratio):
    theme = _mark_theme()
    theme["body"]["values"]["radius"]["value"] = ratio
    assert ThemeTokenView(theme).mark_geometry("planned") == (
        Decimal("0.25"), Decimal("0.125"), 10, Decimal(ratio),
    )


def test_physical_binding_ignores_an_unused_invalid_legacy_reference():
    theme = _physical_only(value=3)
    theme["body"]["roles"]["planned"]["markCornerRadius"] = "missing-legacy-radius"
    geometry = ThemeTokenView(theme).mark_geometry("planned")
    assert geometry[3] == Decimal(0)


def test_malformed_physical_binding_reports_its_own_role_pointer():
    theme = _mark_theme()
    theme["body"]["roles"]["planned"].pop("markCornerRadius")
    # The legacy radius value is a number, not a physical radius token.
    theme["body"]["roles"]["planned"]["cornerRadius"] = "radius"
    with pytest.raises(ThemeTokenError) as error:
        ThemeTokenView(theme).mark_geometry("planned")
    assert error.value.args[0] == "E_THEME_TOKEN_TYPE"
    assert error.value.path == "/body/roles/planned/cornerRadius"


def test_neither_radius_binding_keeps_the_existing_required_binding_error():
    theme = _mark_theme()
    planned = theme["body"]["roles"]["planned"]
    planned.pop("markCornerRadius")
    with pytest.raises(ThemeTokenError) as error:
        ThemeTokenView(theme).mark_geometry("planned")
    assert error.value.args[0] == "E_THEME_ROLE_REQUIRED"
    assert error.value.path == "/body/roles/planned/markCornerRadius"
