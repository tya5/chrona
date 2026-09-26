import pytest
from decimal import Decimal

from chrona.presentation.model.theme_tokens import ThemeTokenError, ThemeTokenView, effective_draft_numeric_theme


def _theme():
    return {"version": "chrona/resolved-theme/v0.2", "kind": "resolved-theme", "body": {
        "values": {"ink": {"type": "color", "value": "#102030"},
                   "body": {"type": "fontFamily", "value": "Test Sans"},
                   "regular": {"type": "fontWeight", "value": 400},
                   "size": {"type": "number", "value": 14}, "line": {"type": "number", "value": 1.4},
                   "spacing": {"type": "number", "value": 0},
                   "transform": {"type": "textTransform", "value": "none"},
                   "numeric": {"type": "numericSpacing", "value": "proportional"}},
        "roles": {"text": {"fill": "ink", "fontFamily": "body", "fontWeight": "regular", "fontSize": "size", "lineHeight": "line",
                           "letterSpacing": "spacing", "textTransform": "transform", "numericSpacing": "numeric"}}, "metrics": {}}}


def test_typed_view_reads_current_resolved_theme_roles_only():
    tokens = ThemeTokenView(_theme())
    assert tokens.color("text") == "#102030"
    assert tokens.font_family() == "Test Sans"
    assert tokens.text_treatment("text").font_size == Decimal(14)


def test_draft_numeric_overlay_changes_only_selected_effective_role():
    declared = _theme()
    declared["body"]["values"]["numeric"]["value"] = "tabular"
    declared["body"]["roles"]["heading"] = dict(declared["body"]["roles"]["text"])
    effective = effective_draft_numeric_theme(declared, ("text",))
    assert ThemeTokenView(declared).text_treatment("text").numeric_spacing == "tabular"
    assert ThemeTokenView(effective).text_treatment("text").numeric_spacing == "proportional"
    assert ThemeTokenView(effective).text_treatment("heading").numeric_spacing == "tabular"


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


def test_background_treatment_preserves_explicit_nondrawable_absence():
    theme = _theme()
    theme["body"]["values"]["order"] = {"type": "number", "value": 10}
    theme["body"]["roles"]["decoration"] = {
        "backgroundTreatment": "none", "backgroundPaintOrder": 10,
    }
    assert ThemeTokenView(theme).background("decoration") == ("none", 10)


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


def test_symbol_resolves_the_full_value_mapping_not_only_the_shape():
    theme = _theme()
    theme["body"]["values"]["gate"] = {"type": "symbol", "value": {
        "shape": "glyph", "viewBox": [10, 10], "parts": [{"d": "M0 0L10 0L10 10L0 10Z", "paint": "fill"}]}}
    theme["body"]["roles"]["milestoneSymbol"] = {"symbol": "gate"}
    value = ThemeTokenView(theme).symbol()
    assert value["shape"] == "glyph"
    assert value["viewBox"] == [10, 10]


def test_variant_symbol_falls_back_to_milestone_symbol_when_a_variant_role_is_unset():
    theme = _theme()
    theme["body"]["values"]["gate"] = {"type": "symbol", "value": {"shape": "diamond"}}
    theme["body"]["roles"]["milestoneSymbol"] = {"symbol": "gate"}
    tokens = ThemeTokenView(theme)
    assert tokens.variant_symbol("planned") == {"shape": "diamond"}
    assert tokens.variant_symbol("actual") == {"shape": "diamond"}
    assert tokens.variant_symbol("baseline") == {"shape": "diamond"}


def test_variant_symbol_uses_its_own_role_when_declared():
    theme = _theme()
    theme["body"]["values"]["gate"] = {"type": "symbol", "value": {"shape": "diamond"}}
    theme["body"]["values"]["ghost"] = {"type": "symbol", "value": {"shape": "circle"}}
    theme["body"]["roles"]["milestoneSymbol"] = {"symbol": "gate"}
    theme["body"]["roles"]["milestoneSymbolBaseline"] = {"symbol": "ghost"}
    tokens = ThemeTokenView(theme)
    assert tokens.variant_symbol("planned") == {"shape": "diamond"}
    assert tokens.variant_symbol("actual") == {"shape": "diamond"}
    assert tokens.variant_symbol("baseline") == {"shape": "circle"}


@pytest.mark.parametrize(("inset", "radius", "expected"), [
    (None, None, (Decimal(0), Decimal(0))),
    (0.2, 0.5, (Decimal("0.2"), Decimal("0.5"))),
    (0.5, None, "progressInset"),
    (0.1, 0.6, "markCornerRadius"),
])
def test_progress_track_is_optional_and_range_checked(inset, radius, expected):
    theme = _theme()
    role = {}
    for name, value, token in (("progressInset", inset, "inset"), ("markCornerRadius", radius, "radius")):
        if value is not None:
            theme["body"]["values"][token] = {"type": "number", "value": value}
            role[name] = token
    theme["body"]["roles"]["progress-fill"] = role
    view = ThemeTokenView(theme)
    if isinstance(expected, str):
        with pytest.raises(ThemeTokenError) as raised:
            view.progress_track("progress-fill")
        assert raised.value.path.endswith(expected)
    else:
        assert view.progress_track("progress-fill") == expected
