import pytest
from decimal import Decimal

from chrona.presentation.model.theme_tokens import ThemeTokenError, ThemeTokenView, effective_draft_numeric_theme
from chrona.presentation.color_scheme import resolve_theme


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
    with pytest.raises(ThemeTokenError, match="E_THEME_TOKEN_TYPE") as error:
        ThemeTokenView(theme).opacity("decoration")
    assert error.value.path == "/body/roles/decoration/opacity"
    assert f"value={value}" in error.value.detail or "valueType=str" in error.value.detail
    assert "expected" in error.value.detail


def test_missing_role_property_is_a_stable_diagnostic():
    with pytest.raises(ThemeTokenError, match="E_THEME_ROLE_REQUIRED") as error:
        ThemeTokenView(_theme()).color("planned")
    assert error.value.path == "/body/roles/planned/fill"
    assert "role='planned', property='fill'" in error.value.detail


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
    with pytest.raises(ThemeTokenError, match="E_THEME_TOKEN_TYPE") as error:
        ThemeTokenView(_theme()).color("text", "fontFamily")
    assert error.value.path == "/body/roles/text/fontFamily"
    assert "role='text', property='fontFamily', token='body'" in error.value.detail
    assert "declaredType=str, expectedType='color'" in error.value.detail


def test_dash_segment_diagnostic_names_role_index_and_numeric_expectation():
    theme = _theme()
    theme["body"]["values"]["dash"] = {"type": "dashPattern", "value": [2, 0]}
    theme["body"]["roles"]["dependency"] = {"dash": "dash"}
    with pytest.raises(ThemeTokenError, match="E_THEME_TOKEN_TYPE") as error:
        ThemeTokenView(theme).dash("dependency")
    assert error.value.path == "/body/roles/dependency/dash/1"
    assert "property='dash[1]'" in error.value.detail and "expected positive finite number" in error.value.detail


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


def test_missing_pattern_reference_diagnostic_is_bounded():
    reference = "private-pattern-" + "x" * 10000
    theme = _theme()
    theme["body"]["values"]["hatch"] = {"type": "pattern", "value": {"kind": "catalog", "ref": reference}}
    theme["body"]["roles"]["summary-bar"] = {"pattern": "hatch"}
    theme["body"]["catalogAssets"] = {"glyphs": {}, "patterns": {}}
    with pytest.raises(ThemeTokenError, match="E_THEME_ASSET_REFERENCE") as error:
        ThemeTokenView(theme).optional_pattern("summary-bar")
    assert "private-pattern-" in error.value.detail
    assert "..." in error.value.detail
    assert len(error.value.detail) < 180


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


def _mark_theme(*, offset="offset", align=None, stack=None):
    values = {"height": {"type": "number", "value": "0.25"},
              "order": {"type": "number", "value": 10},
              "radius": {"type": "number", "value": 0},
              "gap": {"type": "number", "value": 4},
              "padding": {"type": "number", "value": 2}}
    if offset is not None:
        values["offset"] = {"type": "number", "value": "0.125"}
    roles = {}
    for role in ("planned", "actual", "snapshot", "scenario", "missing-actual"):
        roles[role] = {"markHeight": "height", "markPaintOrder": "order", "markCornerRadius": "radius"}
        if offset is not None:
            roles[role]["markOffset"] = offset
        if align is not None:
            roles[role]["align"] = align
    body = {"values": values, "roles": roles}
    if stack is not None:
        body["markStack"] = stack
    return {"version": "chrona/resolved-theme/v0.2", "kind": "resolved-theme", "body": body}


def test_mark_geometry_preserves_declared_offset_and_allows_omission():
    explicit = ThemeTokenView(_mark_theme()).mark_geometry("planned")
    omitted = ThemeTokenView(_mark_theme(offset=None)).mark_geometry("planned")
    assert explicit == (Decimal("0.25"), Decimal("0.125"), 10, Decimal(0))
    assert omitted == (Decimal("0.25"), None, 10, Decimal(0))
    assert ThemeTokenView(_mark_theme(offset=None)).mark_alignment("planned") == "center"


@pytest.mark.parametrize("alignment", ["start", "center", "end"])
def test_mark_alignment_reads_declared_alignment(alignment):
    assert ThemeTokenView(_mark_theme(offset=None, align=alignment)).mark_alignment("planned") == alignment


@pytest.mark.parametrize("height", [0, -0.1, 1.01, "NaN", "Infinity"])
def test_offset_free_mark_geometry_still_requires_finite_height_within_track(height):
    theme = _mark_theme(offset=None)
    theme["body"]["values"]["height"]["value"] = height
    with pytest.raises(ThemeTokenError, match="E_THEME_TOKEN_TYPE"):
        ThemeTokenView(theme).mark_geometry("planned")


def test_mark_stack_resolves_order_groups_frame_and_nonnegative_px_tokens():
    intent = ThemeTokenView(_mark_theme(offset=None, stack={
        "members": [["planned", "missing-actual"], ["actual"]], "gap": "gap",
        "frame": {"roles": ["snapshot", "scenario"], "padding": "padding"},
    })).mark_stack()
    assert intent.members == (("planned", "missing-actual"), ("actual",))
    assert intent.gap == Decimal(4)
    assert intent.frame_roles == ("snapshot", "scenario")
    assert intent.frame_padding == Decimal(2)
    assert ThemeTokenView(_mark_theme()).mark_stack() is None


def test_theme_resolution_preserves_optional_stack_and_keeps_absence_absent():
    from tests.support import synthetic_review as sr

    parts = sr.bundle()
    theme, scheme = parts["theme"], parts["scheme"]
    theme["body"]["markStack"] = {"members": [["planned"]], "gap": "markstack-gap"}
    theme["body"]["values"]["markstack-gap"] = {"type": "number", "value": 3}
    resolved = resolve_theme(theme, scheme, scheme_content_identity="sha256:test")
    assert resolved["body"]["markStack"] == theme["body"]["markStack"]
    del theme["body"]["markStack"]
    resolved_without_stack = resolve_theme(theme, scheme, scheme_content_identity="sha256:test")
    assert "markStack" not in resolved_without_stack["body"]


@pytest.mark.parametrize("stack", [
    {"members": [["planned"], ["planned"]], "gap": "gap"},
    {"members": [["planned", "planned"]], "gap": "gap"},
    {"members": [["unknown"]], "gap": "gap"},
    {"members": [["planned"]], "gap": "missing"},
    {"members": [["planned"]], "gap": "negative"},
    {"members": [["planned"]], "gap": "gap", "frame": {"roles": ["planned"], "padding": "padding"}},
])
def test_mark_stack_rejects_bad_roles_references_and_negative_lengths(stack):
    theme = _mark_theme(offset=None, stack=stack)
    theme["body"]["values"]["negative"] = {"type": "number", "value": -1}
    with pytest.raises(ThemeTokenError, match="E_THEME_TOKEN_TYPE"):
        ThemeTokenView(theme).mark_stack()


def test_mark_stack_rejects_explicit_offsets_on_any_participating_role():
    with pytest.raises(ThemeTokenError) as error:
        ThemeTokenView(_mark_theme(stack={"members": [["planned"]], "gap": "gap"})).mark_stack()
    assert error.value.path == "/body/roles/planned/markOffset"


def test_mark_stack_rejects_lengths_that_cannot_be_completed_as_finite_layout_values():
    theme = _mark_theme(offset=None, stack={"members": [["planned"]], "gap": "huge"})
    theme["body"]["values"]["huge"] = {"type": "number", "value": "1e999"}
    with pytest.raises(ThemeTokenError) as error:
        ThemeTokenView(theme).mark_stack()
    assert error.value.path == "/body/markStack/gap"
    assert "representable" in error.value.detail


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
