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
    theme = {"version": "chrona/theme/v0.9", "kind": "theme", "id": "inside", "body": {
        "values": {}, "roles": {}, "colorBindings": {
            "planned.fill": "accent", "actual.fill": "positive", "snapshot.fill": "neutral",
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
