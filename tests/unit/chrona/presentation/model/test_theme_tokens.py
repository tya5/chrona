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


def test_missing_role_property_is_a_stable_diagnostic():
    with pytest.raises(ThemeTokenError, match="E_THEME_ROLE_REQUIRED") as error:
        ThemeTokenView(_theme()).color("planned")
    assert error.value.path == "/body/roles/planned/fill"


def test_declared_token_type_must_match_the_requested_property():
    with pytest.raises(ThemeTokenError, match="E_THEME_TOKEN_TYPE"):
        ThemeTokenView(_theme()).color("text", "fontFamily")
