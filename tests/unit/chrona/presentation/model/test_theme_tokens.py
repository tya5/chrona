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
    assert ThemeTokenView(theme).optional_background("decoration") == ("none", 10)


def test_optional_background_does_not_infer_absence_for_painted_decoration():
    theme = _theme()
    theme["body"]["roles"]["annotation-note-box"] = {"fill": "text"}
    assert ThemeTokenView(theme).optional_background("annotation-note-box") is None


def test_optional_background_preserves_partial_binding_error():
    theme = _theme()
    theme["body"]["roles"]["decoration"] = {"backgroundPaintOrder": 10}
    with pytest.raises(ThemeTokenError, match="E_THEME_TOKEN_TYPE"):
        ThemeTokenView(theme).optional_background("decoration")


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


def test_catalogued_variant_symbol_resolves_the_frozen_canonical_entry():
    theme = _theme()
    theme["body"]["values"]["gate"] = {"type": "symbol", "value": {"shape": {"catalog": "local:pin"}}}
    theme["body"]["roles"]["milestoneSymbol"] = {"symbol": "gate"}
    entry = {"viewport": {"inlineSize": 8, "blockSize": 8},
             "parts": [{"paint": "fill", "data": "M 0 0 L 8 0 Z"}]}
    theme["body"]["catalogAssets"] = {"glyphs": {"local:pin": entry}, "patterns": {}}
    assert ThemeTokenView(theme).variant_symbol("planned") == {
        "shape": "catalog-glyph", "ref": "local:pin", **entry}


def test_catalogued_pattern_token_resolves_by_exact_authored_reference():
    theme = _theme()
    theme["body"]["values"]["hatch"] = {"type": "pattern", "value": {"kind": "catalog", "ref": "local:hatch"}}
    theme["body"]["roles"]["summary-bar"] = {"pattern": "hatch"}
    entry = {"tile": {"inlineSize": 8, "blockSize": 8}, "angle": 0,
             "densityBasisPoints": 1000, "primitives": [{"kind": "circle", "cx": 4, "cy": 4, "radius": 1}]}
    theme["body"]["catalogAssets"] = {"glyphs": {}, "patterns": {"local:hatch": entry}}
    assert ThemeTokenView(theme).optional_pattern("summary-bar") == {
        "kind": "catalog", "ref": "local:hatch", **entry}


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


def _theme_with_annotation_container(value):
    theme = _theme()
    theme["body"]["values"]["container"] = {"type": "annotationContainer", "value": value}
    theme["body"]["roles"]["annotation"] = {"annotationContainer": "container"}
    return theme


def test_annotation_container_is_none_without_the_binding():
    assert ThemeTokenView(_theme()).annotation_container("annotation") is None


def test_annotation_container_rectangle_and_balloon_are_unchanged_by_465():
    rectangle = ThemeTokenView(_theme_with_annotation_container(
        {"outline": "rectangle", "cornerRadius": 0.2})).annotation_container("annotation")
    assert rectangle.outline == "rectangle" and rectangle.corner_radius == Decimal("0.2")
    assert rectangle.tail_base is None and rectangle.image_ref is None

    balloon = ThemeTokenView(_theme_with_annotation_container(
        {"outline": "balloon", "cornerRadius": 0.1, "tailBaseEm": 0.6})).annotation_container("annotation")
    assert balloon.outline == "balloon" and balloon.tail_base == Decimal("0.6")
    assert balloon.image_ref is None


def test_annotation_container_image_round_trips_reference_and_insets():
    value = {"outline": "image", "image": "chrona:frame", "cornerRadius": 0,
            "sliceInsetsEm": {"top": 0.9, "right": 0.6, "bottom": 0.9, "left": 0.6},
            "contentInsetEm": {"top": 1.1, "right": 0.8, "bottom": 1.1, "left": 0.8}}
    container = ThemeTokenView(_theme_with_annotation_container(value)).annotation_container("annotation")
    assert container.outline == "image"
    assert container.image_ref == "chrona:frame"
    assert container.tail_base is None
    assert container.slice_insets_em == (Decimal("0.9"), Decimal("0.6"), Decimal("0.9"), Decimal("0.6"))
    assert container.content_insets_em == (Decimal("1.1"), Decimal("0.8"), Decimal("1.1"), Decimal("0.8"))


@pytest.mark.parametrize("mutation,expected_suffix", [
    (lambda value: value.pop("image"), "annotationContainer/image"),
    (lambda value: value.update(image=""), "annotationContainer/image"),
    (lambda value: value.update(cornerRadius=0.1), "annotationContainer/cornerRadius"),
    (lambda value: value.pop("sliceInsetsEm"), "annotationContainer/sliceInsetsEm"),
    (lambda value: value["sliceInsetsEm"].update(top=-1), "annotationContainer/sliceInsetsEm"),
    (lambda value: value.pop("contentInsetEm"), "annotationContainer/contentInsetEm"),
])
def test_annotation_container_image_rejects_missing_or_invalid_fields(mutation, expected_suffix):
    value = {"outline": "image", "image": "chrona:frame", "cornerRadius": 0,
            "sliceInsetsEm": {"top": 0.9, "right": 0.6, "bottom": 0.9, "left": 0.6},
            "contentInsetEm": {"top": 1.1, "right": 0.8, "bottom": 1.1, "left": 0.8}}
    mutation(value)
    with pytest.raises(ThemeTokenError) as raised:
        ThemeTokenView(_theme_with_annotation_container(value)).annotation_container("annotation")
    assert raised.value.path.endswith(expected_suffix)
