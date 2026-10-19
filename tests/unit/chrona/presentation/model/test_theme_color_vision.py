"""Legend observations consume only the existing closed Theme vision policy."""
import pytest

from chrona.presentation.model.theme_tokens import ThemeTokenError, ThemeTokenView


def _theme(**body):
    return ThemeTokenView({"version": "chrona/resolved-theme/v0.2", "kind": "resolved-theme",
                           "body": {"values": {}, "roles": {}, **body}})


def test_no_claims_adds_no_simulations():
    assert _theme().color_vision == ()


def test_closed_claims_are_returned_as_immutable_values():
    claims = ["protanopia", "tritanopia"]
    result = _theme(colorVision=claims).color_vision
    claims.append("deuteranopia")
    assert result == ("protanopia", "tritanopia")


@pytest.mark.parametrize("claims", [None, "protanopia", [False], {"mode": "protanopia"}])
def test_invalid_internal_shape_is_rejected_at_the_closed_theme_boundary(claims):
    with pytest.raises(ThemeTokenError) as caught:
        _theme(colorVision=claims).color_vision
    assert caught.value.diagnostic_id == "E_THEME_RESOLVED_SCHEMA"
    assert caught.value.path == "/body/colorVision"
