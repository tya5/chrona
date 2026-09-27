"""Theme admission follows real consumers, not the names used in examples."""

from copy import deepcopy
import json
from pathlib import Path

import pytest

from chrona.presentation.color_scheme import ColorSchemeError, resolve_theme
from chrona.presentation.model.theme_inheritance import resolve_draft_theme
from chrona.presentation.scene.capabilities import theme_role_contract, theme_role_property_consumer
from chrona.resources import safe_load


ROOT = Path(__file__).resolve().parents[4]


def _scheme():
    colors = {name: "#172033" for name in (
        "text", "textMuted", "accent", "positive", "negative", "warning", "neutral",
    )}
    colors.update({"surface": "#FFFFFF", "surfaceRaised": "#F5F7FA"})
    colors.update({name: "#FFFFFF" for name in (
        "insideLabelPlanned", "insideLabelActual", "insideLabelSnapshot", "insideLabelScenario",
    )})
    return {"version": "chrona/color-scheme/v0.2", "kind": "color-scheme", "body": {
        "colors": colors, "categories": {"team-a": "#123456"},
        "provenance": {"kind": "chrona-authored", "source": "test", "license": "pending"},
    }}


def _theme():
    return {"version": "chrona/theme/v0.11", "kind": "theme", "id": "test", "body": {
        "values": {}, "roles": {
            "variance-ahead": {"contrastTreatment": "deemphasized"},
            "variance-on-track": {"contrastTreatment": "required"},
            "variance-behind": {"contrastTreatment": "required"},
            "missing-actual-cell": {"contrastTreatment": "required"},
        }, "colorBindings": {
            "variance-ahead.fill": "text", "variance-on-track.fill": "text",
            "variance-behind.fill": "text", "missing-actual-cell.fill": "text",
        }, "metrics": {},
    }}


def _resolve(theme):
    return resolve_theme(theme, _scheme(), scheme_content_identity="sha256:" + "a" * 64)


@pytest.mark.parametrize(("role", "property_name"), [
    ("variance-behind", "strokeWidth"), ("annotation", "strokeWidth"),
    ("axisMonth", "stroke"), ("groupHeader", "markHeight"),
    ("annotation-note-text", "annotationContainer"), ("baseline", "strokeWidth"),
    ("fiscalAxis", "annotationContainer"), ("customLegend", "markHeight"),
    ("group:team-a", "stroke"), ("group:bad.key", "fill"),
    ("group:team-a", "fontSize"),
    ("dependency", "gradientAngle"), ("text", "shadowBlur"),
    ("icon-mark", "gradientAngle"), ("group-header-band", "annotationContainer"),
])
def test_incapable_direct_role_property_has_exact_pointer(role, property_name):
    theme = _theme()
    theme["body"]["roles"].setdefault(role, {})[property_name] = "unused-token"
    with pytest.raises(ColorSchemeError) as error:
        _resolve(theme)
    assert error.value.diagnostic_id == "E_THEME_ROLE_PROPERTY_UNSUPPORTED"
    assert error.value.source_ref == f"/body/roles/{role}/{property_name}"


@pytest.mark.parametrize("target", ["variance-behind.stroke", "axisMonth.fill", "annotation.stroke",
                                     "dependency.gradientStart", "text.shadowColor"])
def test_incapable_scheme_target_has_exact_pointer(target):
    theme = _theme()
    theme["body"]["colorBindings"][target] = "text"
    with pytest.raises(ColorSchemeError) as error:
        _resolve(theme)
    assert error.value.diagnostic_id == "E_THEME_ROLE_PROPERTY_UNSUPPORTED"
    assert error.value.source_ref == f"/body/colorBindings/{target}"


def test_invalid_direct_binding_keeps_its_pointer_when_scheme_would_overwrite_it():
    theme = _theme()
    theme["body"]["roles"]["variance-behind"]["stroke"] = "unused-token"
    theme["body"]["colorBindings"]["variance-behind.stroke"] = "negative"
    with pytest.raises(ColorSchemeError) as error:
        _resolve(theme)
    assert error.value.diagnostic_id == "E_THEME_ROLE_PROPERTY_UNSUPPORTED"
    assert error.value.source_ref == "/body/roles/variance-behind/stroke"


def test_capable_roles_include_layout_annotation_and_bounded_open_producers():
    theme = _theme()
    theme["body"]["roles"].update({
        "planned": {"shadowBlur": "blur", "shadowFidelity": "optional"},
        "annotation-note-box": {"annotationContainer": "box"},
        "dependency": {"marker": "legend-arrowhead"},
        "fiscalAxis": {"fontSize": "size", "laneBlockSize": "lane"},
        "customLegend": {"strokeWidth": "width"},
    })
    theme["body"]["colorBindings"].update({
        "customLegend.fill": "accent", "fiscalAxis.fill": "accent", "group:team-a.fill": "accent",
    })
    resolved = _resolve(theme)
    assert resolved["body"]["roles"]["annotation-note-box"]["annotationContainer"] == "box"
    assert theme_role_property_consumer("dependency", "marker") == "Scene Path and Layout legend swatch marker"
    assert resolved["body"]["roles"]["fiscalAxis"]["fill"].startswith("__scheme.")
    assert theme_role_property_consumer("axisMonth", "fill") is None
    assert theme_role_property_consumer("annotation-callout-box", "annotationContainer")
    assert theme_role_property_consumer("annotation-highlight-box", "annotationContainer")
    assert theme_role_property_consumer("annotation-arrow-box", "annotationContainer")


def test_every_public_theme_declaration_and_scene_paint_role_has_a_consumer():
    themes = sorted((ROOT / "examples").glob("*/themes/*.yaml"))
    themes += sorted((ROOT / "src/chrona/resources/presets/bundles").glob("*/theme.yaml"))
    assert themes
    for path in themes:
        body = safe_load(path.read_bytes())["body"]
        for role, properties in body.get("roles", {}).items():
            for property_name in properties:
                assert theme_role_property_consumer(role, property_name), (path, role, property_name)
                contract = theme_role_contract(role)
                if contract is not None:
                    assert contract.owner_of(property_name), (path, role, property_name)
        for target in body.get("colorBindings", {}):
            role, property_name = target.rsplit(".", 1)
            assert theme_role_property_consumer(role, property_name), (path, target)

    scenes = sorted((ROOT / "examples").glob("*/generated/*.scene.json"))
    assert scenes
    for path in scenes:
        scene = json.loads(path.read_text(encoding="utf-8"))
        for surface in scene["surfaces"]:
            for primitive in surface["primitives"]:
                contract = theme_role_contract(primitive["visualRole"])
                assert contract is not None and primitive["kind"] in contract.scene_kinds, (
                    path, primitive["visualRole"], primitive["kind"])
                for property_name in ("fill", "stroke"):
                    if primitive["paint"].get(property_name) is not None:
                        assert theme_role_property_consumer(primitive["visualRole"], property_name), (
                            path, primitive["visualRole"], property_name)


def test_every_public_authored_theme_resolves_with_its_declared_scheme():
    observed = set()
    scheme_by_theme = {}
    for context_path in sorted((ROOT / "examples").glob("*/contexts/*.yaml")):
        body = safe_load(context_path.read_bytes()).get("body", {})
        theme_ref, scheme_ref = body.get("theme", {}), body.get("colorScheme", {})
        if not theme_ref.get("address") or not scheme_ref.get("address"):
            continue
        theme_path = context_path.parent.parent / theme_ref["address"]
        scheme_path = context_path.parent.parent / scheme_ref["address"]
        scheme_by_theme[theme_path.resolve()] = scheme_path
        theme = safe_load(theme_path.read_bytes())
        if theme["version"] != "chrona/theme/v0.11":
            continue
        resolve_theme(theme, safe_load(scheme_path.read_bytes()), scheme_content_identity="test")
        observed.add(theme_path.resolve())

    for theme_path in sorted((ROOT / "examples").glob("*/themes/*.yaml")):
        theme = safe_load(theme_path.read_bytes())
        if theme["version"] != "chrona/theme/v0.12":
            continue
        base_path = (theme_path.parent / theme["body"]["extends"]["path"]).resolve()
        scheme_path = scheme_by_theme.get(theme_path.resolve(), scheme_by_theme[base_path])
        resolve_theme(resolve_draft_theme(theme_path), safe_load(scheme_path.read_bytes()),
                      scheme_content_identity="test")
        observed.add(theme_path.resolve())

    library = safe_load((ROOT / "src/chrona/resources/presets/library.yaml").read_bytes())
    for entry in library["entries"]:
        members = entry["members"]
        theme_member, scheme_member = members["theme"], members["colorScheme"]
        theme_path = ROOT / "src/chrona/resources" / theme_member["sourceRoot"] / theme_member["sourcePath"]
        scheme_root = (ROOT / scheme_member["sourceRoot"] if scheme_member["sourceRoot"].startswith("examples/")
                       else ROOT / "src/chrona/resources" / scheme_member["sourceRoot"])
        scheme_path = scheme_root / scheme_member["sourcePath"]
        resolve_theme(safe_load(theme_path.read_bytes()), safe_load(scheme_path.read_bytes()),
                      scheme_content_identity="test")
        observed.add(theme_path.resolve())

    authored = {path.resolve() for path in (ROOT / "examples").glob("*/themes/*.yaml")}
    authored |= {path.resolve() for path in (ROOT / "src/chrona/resources/presets/bundles").glob("*/theme.yaml")}
    assert observed == authored
