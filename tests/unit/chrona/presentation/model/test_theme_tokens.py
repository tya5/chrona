import pytest
from decimal import Decimal

from chrona.presentation.model.theme_tokens import ThemeTokenError, ThemeTokenView


def _theme():
    return {"version": "chrona/resolved-theme/v0.2", "kind": "resolved-theme", "body": {
        "values": {"ink": {"type": "color", "value": "#102030"},
                   "body": {"type": "fontFamily", "value": "Test Sans"},
                   "regular": {"type": "fontWeight", "value": 400},
                   "size": {"type": "number", "value": 14}, "line": {"type": "number", "value": 1.4}},
        "roles": {"text": {"fill": "ink", "fontFamily": "body", "fontWeight": "regular", "fontSize": "size", "lineHeight": "line"}}, "metrics": {}}}


def test_typed_view_reads_current_resolved_theme_roles_only():
    tokens = ThemeTokenView(_theme())
    assert tokens.color("text") == "#102030"
    assert tokens.font_family() == "Test Sans"
    assert tokens.typography("text") == ("Test Sans", 400, Decimal(14), Decimal("1.4"))


@pytest.mark.parametrize("value", [0, 1, "0.12"])
def test_typed_view_resolves_finite_role_opacity(value):
    theme = _theme()
    theme["body"]["values"]["alpha"] = {"type": "number", "value": value}
    theme["body"]["roles"]["decoration"] = {"opacity": "alpha"}
    assert ThemeTokenView(theme).opacity("decoration") == float(value)


@pytest.mark.parametrize("value", [-0.1, 1.1, "NaN", "Infinity"])
def test_typed_view_rejects_out_of_range_or_non_finite_role_opacity(value):
    theme = _theme()
    theme["body"]["values"]["alpha"] = {"type": "number", "value": value}
    theme["body"]["roles"]["decoration"] = {"opacity": "alpha"}
    with pytest.raises(ThemeTokenError, match="E_THEME_TOKEN_TYPE"):
        ThemeTokenView(theme).opacity("decoration")


def test_missing_role_property_is_a_stable_diagnostic():
    with pytest.raises(ThemeTokenError, match="E_THEME_ROLE_REQUIRED") as error:
        ThemeTokenView(_theme()).color("planned")
    assert error.value.path == "/body/roles/planned/fill"


def test_declared_token_type_must_match_the_requested_property():
    with pytest.raises(ThemeTokenError, match="E_THEME_TOKEN_TYPE"):
        ThemeTokenView(_theme()).color("text", "fontFamily")


@pytest.mark.parametrize("value", [0, -1, 1.1])
def test_summary_bar_height_requires_one_positive_lane_relative_token(value):
    theme = _theme()
    theme["body"]["values"]["height"] = {"type": "number", "value": value}
    theme["body"]["roles"]["summary-bar"] = {"markHeight": "height"}
    with pytest.raises(ThemeTokenError, match="E_THEME_TOKEN_TYPE"):
        ThemeTokenView(theme).summary_bar_height("summary-bar")


def test_summary_bar_height_resolves_its_theme_owned_value():
    theme = _theme()
    theme["body"]["values"]["height"] = {"type": "number", "value": "0.25"}
    theme["body"]["roles"]["summary-bar"] = {"markHeight": "height"}
    assert ThemeTokenView(theme).summary_bar_height("summary-bar") == Decimal("0.25")
