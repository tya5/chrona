import pytest

from chrona.presentation.color_scheme import (
    ColorSchemeError, _annotation_kinds, _canvas_texture, _contrast_policy, _horizontal_scales,
    _writing_modes, resolve_color_scheme, resolve_theme,
)


def _scheme():
    return {"version": "chrona/color-scheme/v0.2", "kind": "color-scheme", "body": {
        "colors": {"surface": "#FFFFFF", "surfaceRaised": "#F5F7FA", "text": "#172033",
                   "textMuted": "#4B5563", "accent": "#1D4ED8", "positive": "#047857",
                   "negative": "#B91C1C", "warning": "#A16207", "neutral": "#475569",
                   "insideLabelPlanned": "#FFFFFF", "insideLabelActual": "#FFFFFF",
                   "insideLabelSnapshot": "#FFFFFF", "insideLabelScenario": "#FFFFFF"},
        "categories": {"team-a": "#123456"},
        "provenance": {"kind": "author", "source": "test", "license": "test"},
    }}


def _theme():
    return {"version": "chrona/theme/v0.15", "kind": "theme", "body": {
        "values": {}, "roles": {
            "variance-ahead": {"contrastTreatment": "deemphasized"},
            "variance-on-track": {"contrastTreatment": "required"},
            "variance-behind": {"contrastTreatment": "required"},
            "missing-actual-cell": {"contrastTreatment": "required"},
        }, "colorBindings": {
            "variance-ahead.fill": "positive", "variance-on-track.fill": "textMuted",
            "variance-behind.fill": "negative", "missing-actual-cell.fill": "textMuted",
        }, "metrics": {},
    }}


def test_scheme_provenance_diagnostic_names_missing_fields():
    scheme = _scheme()
    del scheme["body"]["provenance"]["license"]
    with pytest.raises(ColorSchemeError, match="E_SCHEME_PROVENANCE") as error:
        resolve_color_scheme(scheme, content_identity="sha256:" + "a" * 64)
    assert error.value.source_ref == "/body/provenance"
    assert "missing or empty provenance fields=('license',)" in error.value.detail


def test_scheme_intent_diagnostic_names_color_binding_and_unknown_intent():
    theme = _theme()
    theme["body"]["colorBindings"]["annotation-note-box.fill"] = "ultraviolet"
    with pytest.raises(ColorSchemeError, match="E_SCHEME_INTENT_UNKNOWN") as error:
        resolve_theme(theme, _scheme(), scheme_content_identity="sha256:" + "a" * 64)
    assert error.value.source_ref == "/body/colorBindings/annotation-note-box.fill"
    assert "intent='ultraviolet'" in error.value.detail
    assert "declared intent/category" in error.value.detail


def test_color_scale_mapping_diagnostic_names_unresolved_category_slot():
    theme = _theme()
    theme["body"]["colorScales"] = {"owners": {"palette": ["team-ghost"]}}
    with pytest.raises(ColorSchemeError, match="E_PRESENTATION_SCALE_MAPPING") as error:
        resolve_theme(theme, _scheme(), scheme_content_identity="sha256:" + "a" * 64)
    assert error.value.source_ref == "/body/colorScales/owners/palette"
    assert "missing category slots=('team-ghost',)" in error.value.detail


def test_scheme_schema_diagnostic_names_wrong_version_and_color_container_type():
    scheme = _scheme()
    scheme["version"] = "chrona/color-scheme/v99"
    scheme["body"]["colors"] = []
    with pytest.raises(ColorSchemeError, match="E_SCHEME_SCHEMA") as error:
        resolve_color_scheme(scheme, content_identity="sha256:" + "a" * 64)
    assert "version='chrona/color-scheme/v99'" in error.value.detail
    assert "colorsType=list" in error.value.detail


def test_theme_binding_diagnostic_names_bad_theme_kind():
    theme = _theme()
    theme["kind"] = "color-scheme"
    with pytest.raises(ColorSchemeError, match="E_SCHEME_THEME_BINDING") as error:
        resolve_theme(theme, _scheme(), scheme_content_identity="sha256:" + "a" * 64)
    assert error.value.source_ref == "/"
    assert "kind='color-scheme'" in error.value.detail
    assert "expected theme v0.15" in error.value.detail


def test_theme_binding_diagnostic_names_invalid_body_and_binding_types():
    theme = _theme()
    theme["body"] = []
    with pytest.raises(ColorSchemeError, match="E_SCHEME_THEME_BINDING") as error:
        resolve_theme(theme, _scheme(), scheme_content_identity="sha256:" + "a" * 64)
    assert error.value.source_ref == "/body/colorBindings"
    assert "bodyType=list" in error.value.detail
    assert "colorBindingsType=NoneType" in error.value.detail


def test_theme_binding_diagnostic_names_unsupported_binding_property():
    theme = _theme()
    theme["body"]["colorBindings"]["variance-ahead.width"] = "positive"
    with pytest.raises(ColorSchemeError, match="E_SCHEME_THEME_BINDING") as error:
        resolve_theme(theme, _scheme(), scheme_content_identity="sha256:" + "a" * 64)
    assert error.value.source_ref == "/body/colorBindings/variance-ahead.width"
    assert "property='width'" in error.value.detail
    assert "fill, stroke, gradientStart" in error.value.detail


def test_theme_binding_diagnostic_names_invalid_color_scales_container():
    theme = _theme()
    theme["body"]["colorScales"] = ["scale-9"]
    with pytest.raises(ColorSchemeError, match="E_SCHEME_THEME_BINDING") as error:
        resolve_theme(theme, _scheme(), scheme_content_identity="sha256:" + "a" * 64)
    assert error.value.source_ref == "/body/colorScales"
    assert "colorScalesType=list" in error.value.detail
    assert "expected mapping of scale identifiers" in error.value.detail


def test_scheme_required_intent_diagnostic_names_missing_color_field():
    scheme = _scheme()
    del scheme["body"]["colors"]["warning"]
    with pytest.raises(ColorSchemeError, match="E_SCHEME_SCHEMA") as error:
        resolve_color_scheme(scheme, content_identity="sha256:" + "a" * 64)
    assert error.value.source_ref == "/body/colors"
    assert "missing intents=('warning',)" in error.value.detail


def test_scheme_schema_diagnostic_bounds_oversized_kind():
    scheme = _scheme()
    scheme["kind"] = "secret-kind-" + "x" * 10000
    with pytest.raises(ColorSchemeError, match="E_SCHEME_SCHEMA") as error:
        resolve_color_scheme(scheme, content_identity="sha256:" + "a" * 64)
    assert "secret-kind-" in error.value.detail
    assert len(error.value.detail) < 300


def test_unknown_binding_diagnostic_bounds_oversized_target_and_intent():
    theme = _theme()
    target = "unknown-role-" + "x" * 10000 + ".fill"
    theme["body"]["colorBindings"][target] = "unknown-intent-" + "y" * 10000
    with pytest.raises(ColorSchemeError, match="E_SCHEME_INTENT_UNKNOWN") as error:
        resolve_theme(theme, _scheme(), scheme_content_identity="sha256:" + "a" * 64)
    assert error.value.source_ref.endswith("<long-target>")
    assert "unknown-role-" in error.value.detail
    assert "unknown-intent-" in error.value.detail
    assert len(error.value.detail) < 300


def test_annotation_kind_diagnostics_name_kind_and_invalid_alternatives():
    with pytest.raises(ColorSchemeError, match="E_THEME_ANNOTATION_KIND_TEMPLATE") as error:
        _annotation_kinds(declared={"launch": {"label": "Launch", "colorAlso": ["footer"], "color": "accent"}}, colors={"accent": "#123456"})
    assert error.value.source_ref == "/body/annotationKinds/launch/colorAlso"
    assert "colorIntent='accent'" in error.value.detail


def test_annotation_kind_intent_diagnostic_names_unknown_color_choice():
    with pytest.raises(ColorSchemeError, match="E_SCHEME_INTENT_UNKNOWN") as intent_error:
        _annotation_kinds(declared={"launch": {"label": "Launch", "color": "violet-ink"}}, colors={})
    assert "intent='violet-ink'" in intent_error.value.detail


def test_horizontal_scale_token_diagnostic_names_role_token_and_expected_type():
    with pytest.raises(ColorSchemeError, match="E_THEME_TOKEN_TYPE") as error:
        _horizontal_scales(declared_roles={"heading": {"horizontalScale": "wide"}},
                           values={"wide": {"type": "text", "value": "large"}})
    assert error.value.source_ref == "/body/roles/heading/horizontalScale"
    assert "token='wide'" in error.value.detail and "expected number token" in error.value.detail


def test_writing_mode_diagnostic_names_role_token_and_closed_values():
    with pytest.raises(ColorSchemeError, match="E_THEME_TOKEN_TYPE") as error:
        _writing_modes(declared_roles={"vertical-label": {"writingMode": "mode"}},
                       values={"mode": {"type": "writingMode", "value": "diagonal"}})
    assert error.value.source_ref == "/body/roles/vertical-label/writingMode"
    assert "token='mode'" in error.value.detail and "horizontal or vertical" in error.value.detail


def test_contrast_policy_diagnostic_names_member_and_declared_alternatives():
    with pytest.raises(ColorSchemeError, match="E_THEME_CONTRAST_POLICY") as error:
        _contrast_policy({"stateText": "critical"})
    assert error.value.source_ref == "/body/contrastPolicy/stateText"
    assert "expected one of none, warning, error" in error.value.detail


def test_canvas_texture_diagnostic_names_binding_and_expected_pattern_kind():
    with pytest.raises(ColorSchemeError, match="E_THEME_ROLE_PROPERTY_UNSUPPORTED") as error:
        _canvas_texture(roles={"canvas-texture": {"pattern": "linen"}},
                       values={"linen": {"type": "pattern", "value": {"kind": "inline"}}})
    assert error.value.source_ref == "/body/roles/canvas-texture/pattern"
    assert "token='linen'" in error.value.detail and "expected catalog or seeded pattern" in error.value.detail
