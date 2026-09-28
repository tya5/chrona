import pytest

from chrona.presentation.color_scheme import ColorSchemeError, resolve_color_scheme, resolve_theme


def scheme():
    return {"version": "chrona/color-scheme/v0.2", "kind": "color-scheme", "body": {"colors": {"surface": "#FFFFFF", "surfaceRaised": "#F5F7FA", "text": "#172033", "textMuted": "#4B5563", "accent": "#1D4ED8", "positive": "#047857", "negative": "#B91C1C", "warning": "#A16207", "neutral": "#475569", "insideLabelPlanned": "#FFFFFF", "insideLabelActual": "#FFFFFF", "insideLabelSnapshot": "#FFFFFF", "insideLabelScenario": "#FFFFFF"}, "categories": {"team-a": "#123456", "team-b": "#654321"}, "provenance": {"kind": "chrona-authored", "source": "test", "license": "pending"}}}


def test_scheme_requires_provenance_and_resolves_named_categories():
    value = resolve_color_scheme(scheme(), content_identity="sha256:" + "a" * 64)
    assert value["category:team-a"] == "#123456"
    del scheme()["body"]["provenance"]
    bad = scheme(); del bad["body"]["provenance"]
    with pytest.raises(ColorSchemeError, match="E_SCHEME_PROVENANCE"):
        resolve_color_scheme(bad, content_identity="sha256:" + "a" * 64)


def test_scheme_rejects_insufficient_text_contrast():
    bad = scheme(); bad["body"]["colors"]["text"] = "#F5F7FA"
    with pytest.raises(ColorSchemeError, match="E_SCHEME_CONTRAST"):
        resolve_color_scheme(bad, content_identity="sha256:" + "a" * 64)


def test_theme_validates_each_inside_label_role_against_its_host_mark():
    theme = {"version": "chrona/theme/v0.11", "kind": "theme", "id": "inside", "body": {
        "values": {}, "roles": {
            "variance-ahead": {"contrastTreatment": "deemphasized"},
            "variance-on-track": {"contrastTreatment": "required"},
            "variance-behind": {"contrastTreatment": "required"},
            "missing-actual-cell": {"contrastTreatment": "required"},
        }, "colorBindings": {
            "planned.fill": "accent", "actual.fill": "positive", "snapshot.fill": "neutral",
            "variance-ahead.fill": "positive", "variance-on-track.fill": "textMuted",
            "variance-behind.fill": "negative", "missing-actual-cell.fill": "textMuted",
            "member-label-inside-planned.fill": "insideLabelPlanned",
            "member-label-inside-actual.fill": "insideLabelActual",
            "member-label-inside-snapshot.fill": "insideLabelSnapshot",
            "member-label-inside-scenario.fill": "insideLabelScenario",
        }, "metrics": {},
    }}
    resolved = resolve_theme(theme, scheme(), scheme_content_identity="sha256:" + "a" * 64)
    assert "member-label-inside-planned" in resolved["body"]["roles"]
    theme["body"]["colorBindings"]["member-label-inside-planned.fill"] = "accent"
    with pytest.raises(ColorSchemeError, match="E_SCHEME_INSIDE_LABEL_CONTRAST"):
        resolve_theme(theme, scheme(), scheme_content_identity="sha256:" + "a" * 64)


def test_theme_state_text_requires_declared_treatment_and_composited_floor():
    theme = {"version": "chrona/theme/v0.11", "kind": "theme", "id": "state", "body": {
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
    resolve_theme(theme, scheme(), scheme_content_identity="sha256:" + "a" * 64)
    theme["body"]["roles"]["variance-behind"]["contrastTreatment"] = "deemphasized"
    with pytest.raises(ColorSchemeError, match="E_SCHEME_STATE_TEXT_TREATMENT"):
        resolve_theme(theme, scheme(), scheme_content_identity="sha256:" + "a" * 64)
    theme["body"]["roles"]["variance-behind"]["contrastTreatment"] = "required"
    del theme["body"]["roles"]["variance-ahead"]["contrastTreatment"]
    with pytest.raises(ColorSchemeError) as error:
        resolve_theme(theme, scheme(), scheme_content_identity="sha256:" + "a" * 64)
    assert error.value.diagnostic_id == "E_SCHEME_STATE_TEXT_TREATMENT"
    assert error.value.source_ref == "/body/roles/variance-ahead"


def _note_theme():
    theme = {"version": "chrona/theme/v0.11", "kind": "theme", "id": "note", "body": {
        "values": {}, "roles": {
            "variance-ahead": {"contrastTreatment": "deemphasized"},
            "variance-on-track": {"contrastTreatment": "required"},
            "variance-behind": {"contrastTreatment": "required"},
            "missing-actual-cell": {"contrastTreatment": "required"},
            "annotation-note-box": {},
            "annotation-note-text": {"contrastTreatment": "required"},
        }, "colorBindings": {
            "variance-ahead.fill": "positive",
            "variance-on-track.fill": "textMuted",
            "variance-behind.fill": "negative",
            "missing-actual-cell.fill": "textMuted",
            "annotation-note-box.fill": "accent",
            "annotation-note-text.fill": "text",
        }, "metrics": {},
    }}
    return theme


def test_annotation_note_text_requires_required_treatment():
    theme = _note_theme()
    theme["body"]["roles"]["annotation-note-text"]["contrastTreatment"] = "deemphasized"
    with pytest.raises(ColorSchemeError) as error:
        resolve_theme(theme, scheme(), scheme_content_identity="sha256:" + "a" * 64)
    assert error.value.diagnostic_id == "E_SCHEME_STATE_TEXT_TREATMENT"
    assert error.value.source_ref == "/body/roles/annotation-note-text/contrastTreatment"


def test_annotation_note_box_requires_effective_flat_opaque_fill():
    theme = _note_theme()
    theme["body"]["colorBindings"].pop("annotation-note-box.fill")
    with pytest.raises(ColorSchemeError) as error:
        resolve_theme(theme, scheme(), scheme_content_identity="sha256:" + "a" * 64)
    assert error.value.diagnostic_id == "E_SCHEME_ANNOTATION_NOTE_GROUND"
    assert error.value.source_ref == "/body/roles/annotation-note-box/fill"

    theme = _note_theme()
    theme["body"]["roles"]["annotation-note-box"]["opacity"] = "note-opacity"
    theme["body"]["values"]["note-opacity"] = {"type": "number", "value": 0.5}
    with pytest.raises(ColorSchemeError) as error:
        resolve_theme(theme, scheme(), scheme_content_identity="sha256:" + "a" * 64)
    assert error.value.diagnostic_id == "E_SCHEME_ANNOTATION_NOTE_GROUND"
    assert error.value.source_ref == "/body/roles/annotation-note-box/opacity"


def test_annotation_note_box_accepts_scheme_inserted_opaque_fill_and_default_opacity():
    resolved = resolve_theme(_note_theme(), scheme(), scheme_content_identity="sha256:" + "a" * 64)
    assert resolved["body"]["roles"]["annotation-note-box"]["fill"].startswith("__scheme.accent.")


def test_annotation_note_box_rejects_gradient_or_pattern_ground_with_exact_pointer():
    theme = _note_theme()
    theme["body"]["colorBindings"]["annotation-note-box.gradientStart"] = "accent"
    with pytest.raises(ColorSchemeError) as error:
        resolve_theme(theme, scheme(), scheme_content_identity="sha256:" + "a" * 64)
    assert error.value.diagnostic_id == "E_SCHEME_ANNOTATION_NOTE_GROUND"
    assert error.value.source_ref == "/body/colorBindings/annotation-note-box.gradientStart"

    theme = _note_theme()
    theme["body"]["roles"]["annotation-note-box"]["pattern"] = "box-pattern"
    with pytest.raises(ColorSchemeError) as error:
        resolve_theme(theme, scheme(), scheme_content_identity="sha256:" + "a" * 64)
    assert error.value.diagnostic_id == "E_SCHEME_ANNOTATION_NOTE_GROUND"
    assert error.value.source_ref == "/body/roles/annotation-note-box/pattern"
