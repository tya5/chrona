from hashlib import sha256
from pathlib import Path

import pytest
import yaml

from chrona.presentation.contracts import PresentationIngressRejected
from chrona.presentation.contracts.resources import ClosureIdentity, IconCatalogContract, freeze
from chrona.presentation.model.closure import ClosureError, ClosureResource, _resolve_theme_catalog_assets, resolve_render_context
from chrona.storage.revision_store import LocalSnapshotReader
from chrona.storage.snapshot_paths import snapshot_directory


def _ref(kind, identifier, address, payload, token="snapshot-1"):
    return {"id": identifier, "kind": kind, "store": {"provider": "local", "identity": "closure-test"}, "address": address, "revision": {"token": token}, "contentIdentity": f"sha256:{sha256(payload).hexdigest()}"}


def _write(root: Path, address: str, value: dict, token="snapshot-1"):
    payload = yaml.safe_dump(value, sort_keys=True).encode()
    path = snapshot_directory(root, token) / address
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    return payload


def test_closure_rejects_path_escape_before_reading_snapshot(tmp_path):
    reader = LocalSnapshotReader(tmp_path, "closure-test")
    with pytest.raises(ClosureError, match="E_IMMUTABLE_SNAPSHOT_REQUIRED"):
        resolve_render_context({"id": "ctx", "kind": "render-context", "store": {"provider": "local", "identity": "closure-test"}, "address": "../context.yaml", "revision": {"token": "snapshot-1"}, "contentIdentity": "sha256:" + "0" * 64}, reader)


def _catalog_resource(*, glyphs=None, patterns=None):
    contract = IconCatalogContract(
        ClosureIdentity("icon-catalog", "local-assets", "snapshot-1", "sha256:" + "a" * 64),
        "chrona/icon-catalog/v0.5", "local", (), freeze({
            "sourceKind": "theme-asset-source", "sourceContentIdentity": "sha256:" + "b" * 64,
            "license": {"spdx": "MIT", "notice": "test"}}),
        freeze({}), (), (), freeze({}), freeze(glyphs or {}), freeze(patterns or {}))
    return ClosureResource("icon-catalog", "local-assets", "snapshot-1", "sha256:" + "a" * 64, contract)


def test_theme_catalog_glyph_closes_and_returns_exact_authored_reference():
    theme = {"body": {"values": {"symbol": {"type": "symbol", "value": {
        "shape": {"catalog": "local:pin"}}}}, "roles": {"milestoneSymbol": {"symbol": "symbol"}}}}
    resource = _catalog_resource(glyphs={"pin": {"viewport": {"inlineSize": 8, "blockSize": 8},
                                                  "parts": [{"paint": "fill", "data": "M 0 0 L 8 0 Z"}]}})
    glyphs, patterns = _resolve_theme_catalog_assets(theme, (resource,))
    assert "local:pin" in glyphs and not patterns


def test_theme_catalog_reference_error_has_exact_theme_pointer_and_reference():
    theme = {"body": {"values": {"symbol": {"type": "symbol", "value": {
        "shape": {"catalog": "missing:pin"}}}}, "roles": {"milestoneSymbol": {"symbol": "symbol"}}}}
    with pytest.raises(ClosureError, match="E_THEME_ASSET_REFERENCE") as error:
        _resolve_theme_catalog_assets(theme, (_catalog_resource(glyphs={"pin": {}}),))
    assert error.value.source_ref == "/body/values/symbol/value/shape/catalog"
    assert "missing:pin" in error.value.detail


def test_catalog_pattern_is_rejected_on_symbol_role_at_theme_pointer():
    theme = {"body": {"values": {"pattern": {"type": "pattern", "value": {
        "kind": "catalog", "ref": "local:hatch"}},
        "fill": {"type": "color", "value": "#111111"},
        "stroke": {"type": "color", "value": "#222222"}},
        "roles": {"milestoneSymbol": {"pattern": "pattern", "fill": "fill", "stroke": "stroke"}}}}
    entry = {"tile": {"inlineSize": 8, "blockSize": 8}, "angle": 0,
             "densityBasisPoints": 1000, "primitives": [{"kind": "circle", "cx": 4, "cy": 4, "radius": 1}]}
    with pytest.raises(ClosureError, match="E_THEME_ROLE_PROPERTY_UNSUPPORTED") as error:
        _resolve_theme_catalog_assets(theme, (_catalog_resource(patterns={"hatch": entry}),))
    assert error.value.source_ref == "/body/roles/milestoneSymbol/pattern"


def test_catalog_pattern_is_rejected_on_note_box_role_at_theme_pointer():
    theme = {"body": {"values": {
        "pattern": {"type": "pattern", "value": {"kind": "catalog", "ref": "local:hatch"}},
        "fill": {"type": "color", "value": "#111111"},
        "stroke": {"type": "color", "value": "#FFFFFF"},
    }, "roles": {"annotation-note-box": {
        "pattern": "pattern", "fill": "fill", "stroke": "stroke",
    }}}}
    entry = {"tile": {"inlineSize": 8, "blockSize": 8}, "angle": 0,
             "densityBasisPoints": 1000,
             "primitives": [{"kind": "circle", "cx": 4, "cy": 4, "radius": 1}]}
    with pytest.raises(ClosureError, match="E_THEME_ROLE_PROPERTY_UNSUPPORTED") as error:
        _resolve_theme_catalog_assets(theme, (_catalog_resource(patterns={"hatch": entry}),))
    assert error.value.source_ref == "/body/roles/annotation-note-box/pattern"


def test_catalog_pattern_requires_opaque_role_paints():
    theme = {"body": {"values": {"pattern": {"type": "pattern", "value": {
        "kind": "catalog", "ref": "local:hatch"}}, "fill": {"type": "color", "value": "#111111"}},
        "roles": {"summary-bar": {"pattern": "pattern", "fill": "fill"}}}}
    with pytest.raises(ClosureError, match="E_THEME_ROLE_REQUIRED") as error:
        _resolve_theme_catalog_assets(theme, ())
    assert error.value.source_ref == "/body/roles/summary-bar/stroke"


@pytest.mark.parametrize(("property_name", "token"), [
    ("fill", {"type": "color", "value": "#11111180"}),
    ("opacity", {"type": "number", "value": 0.5}),
])
def test_catalog_pattern_rejects_nonopaque_paint_or_opacity(property_name, token):
    values = {"pattern": {"type": "pattern", "value": {"kind": "catalog", "ref": "local:hatch"}},
              "fill": {"type": "color", "value": "#111111"},
              "stroke": {"type": "color", "value": "#222222"},
              "opacity": {"type": "number", "value": 1}}
    roles = {"summary-bar": {"pattern": "pattern", "fill": "fill", "stroke": "stroke", "opacity": "opacity"}}
    values[property_name] = token
    roles["summary-bar"][property_name] = property_name
    theme = {"body": {"values": values, "roles": roles}}
    with pytest.raises(ClosureError, match="E_THEME_ROLE_PROPERTY_UNSUPPORTED") as error:
        _resolve_theme_catalog_assets(theme, ())
    assert error.value.source_ref == f"/body/roles/summary-bar/{property_name}"


@pytest.mark.parametrize(("property_name", "token_id"), [
    ("strokeWidth", "width"), ("dash", "dash"),
    ("strokeLineCap", "cap"), ("gradientStart", "gradient"),
    ("backgroundTreatment", "outline"),
])
def test_catalog_pattern_rejects_conflicting_role_paint_at_exact_pointer(property_name, token_id):
    theme = {"body": {"values": {
        "pattern": {"type": "pattern", "value": {"kind": "catalog", "ref": "local:hatch"}},
        "fill": {"type": "color", "value": "#111111"},
        "stroke": {"type": "color", "value": "#FFFFFF"}},
        "roles": {"summary-bar": {"pattern": "pattern", "fill": "fill", "stroke": "stroke",
                                  property_name: token_id}}}}
    with pytest.raises(ClosureError, match="E_THEME_ROLE_PROPERTY_UNSUPPORTED") as error:
        _resolve_theme_catalog_assets(theme, ())
    assert error.value.source_ref == f"/body/roles/summary-bar/{property_name}"


def test_v05_closure_binds_theme_scheme_and_layout_separately(tmp_path):
    project = {"version": "timeline/v0.7", "project": {"id": "p"}, "objects": {}}
    view = {"version": "chrona/view/v0.26", "kind": "view", "id": "v", "body": {}}
    theme = {"version": "chrona/theme/v0.15", "kind": "theme", "id": "t", "body": {"values": {}, "roles": {}, "colorBindings": {"text.fill": "text"}}}
    scheme = {"version": "chrona/color-scheme/v0.2", "kind": "color-scheme", "id": "s", "body": {"colors": {"surface": "#FFFFFF", "surfaceRaised": "#F5F7FA", "text": "#172033", "textMuted": "#4B5563", "accent": "#1D4ED8", "positive": "#047857", "negative": "#B91C1C", "warning": "#A16207", "neutral": "#475569", "insideLabelPlanned": "#FFFFFF", "insideLabelActual": "#FFFFFF", "insideLabelSnapshot": "#FFFFFF", "insideLabelScenario": "#FFFFFF"}, "categories": {"default": "#112233"}, "suitability": {"background": "light", "colorVision": ["none-claimed"], "print": "not-claimed"}, "provenance": {"kind": "chrona-authored", "source": "test", "license": "pending"}}}
    layout = {"version": "chrona/layout-profile/v0.10", "id": "l", "flowDirection": "horizontal", "dependencyNetworkFlowDirection": "horizontal", "requiredThemeTokens": [], "reviewSurface": {"rowDistribution": "pack", "backgroundExtents": {"rowBand": "table", "groupBand": "timeline", "groupHeaderBand": "both", "calendarClosed": "timeline"}, "annotationRouting": {"maxBends": 4, "maxDetourRatio": 2}}, "root": {}}
    refs = {}
    for name, kind, identifier, value in (
        ("project", "project", "p", project), ("view", "view", "v", view),
        ("theme", "theme", "t", theme), ("scheme", "color-scheme", "s", scheme), ("layout", "layout-profile", "l", layout),
    ):
        payload = _write(tmp_path, f"{name}.yaml", value)
        refs[name] = _ref(kind, identifier, f"{name}.yaml", payload)
    identity = "sha256:" + "a" * 64
    context = {
            "version": "chrona/render-context/v0.17", "kind": "render-context", "id": "ctx",
        "body": {
            "project": refs["project"], "view": refs["view"], "theme": refs["theme"],
            "colorScheme": refs["scheme"], "layout": refs["layout"], "inputs": {},
            "environment": {"viewport": {"inlineSize": 1000, "blockSize": 600}, "locale": "en-US", "fontMetrics": {"algorithm": "declared-metrics-v3", "assets": [{"family": "Noto Sans", "weight": 400, "metrics": {"locator": {"provider": "context", "address": "fonts/noto.json"}, "contentIdentity": identity}, "font": {"locator": {"provider": "context", "address": "fonts/noto.ttf"}, "contentIdentity": identity}}], "missingFont": "diagnose"}, "scenePrecision": 3},
            "target": {"kind": "svg", "capabilities": ["accessibleText"], "visualProfile": "chrona-output/visual/v0.5-baseline"},
        },
    }
    payload = _write(tmp_path, "context-v05.yaml", context)
    with pytest.raises(PresentationIngressRejected) as error:
        resolve_render_context(_ref("render-context", "ctx", "context-v05.yaml", payload), LocalSnapshotReader(tmp_path, "closure-test"))
    assert {item.resource_kind for item in error.value.diagnostics} == {"view", "layout-profile"}
    assert {item.pointer for item in error.value.diagnostics} >= {"/body"}
