"""Frame glyph paint is a separate optional consumer, not a Rect-role alias."""
from pathlib import Path

import pytest
import yaml

from chrona.presentation.color_scheme import resolve_theme
from chrona.presentation.model.theme_role_consumers import unread_roles
from chrona.presentation.scene.capabilities import theme_role_contract, theme_role_property_consumer
from tests.support import synthetic_review as sr


@pytest.mark.parametrize("role", ["frame-glyph", "frame-glyph-marquee", "frame-glyph-panel-2"])
def test_catalogue_run_properties_have_explicit_responsibility_owners(role):
    contract = theme_role_contract(role)
    assert contract.scene_kinds == frozenset({"Symbol"})
    assert contract.properties == frozenset({"fill", "stroke", "opacity", "artworkFidelity", "symbol", "glyphSize", "glyphPitch"})
    for name in ("symbol", "glyphSize", "glyphPitch"):
        assert contract.owner_of(name) == "Layout/Scene completed geometry"
    for name in ("fill", "stroke", "opacity", "artworkFidelity"):
        assert contract.owner_of(name) == "Scene paint"
    assert theme_role_property_consumer(role, "symbolHeight") is None  # track ratio is not a physical glyph size
    assert theme_role_property_consumer(role, "pattern") is None
    assert theme_role_property_consumer(role, "frameCornerRadius") is None


def test_existing_rect_frame_named_glyph_is_not_reinterpreted():
    assert theme_role_contract("region-frame-glyph") == theme_role_contract("region-frame")
    assert theme_role_contract("region-frame-glyph").scene_kinds == frozenset({"Rect"})
    assert theme_role_property_consumer("region-frame-glyph", "symbol") is None


@pytest.mark.parametrize("role", ["frame-glyph-1bad", "frame-glyph-", "frame-glyph-Upper"])
def test_malformed_suffix_is_not_a_glyph_consumer(role):
    assert theme_role_contract(role) is None
    assert theme_role_property_consumer(role, "glyphSize") is None


def test_named_glyph_role_is_read_only_when_its_frame_paint_is_named():
    theme = {"roles": {"frame-glyph-marquee": {"symbol": "bulb"}, "frame-glyph-unused": {}}, "colorBindings": {}}
    profile = {"root": {"id": "any-node", "frame": {"paint": "marquee"}}}
    assert unread_roles(theme, (profile,)) == frozenset({"frame-glyph-unused"})
    assert unread_roles(theme, ()) == frozenset({"frame-glyph-marquee", "frame-glyph-unused"})


def test_reusable_marquee_patch_resolves_its_ink_independently_of_the_panel():
    root = Path(__file__).resolve().parents[5]
    fixture = yaml.safe_load((root / "tests/fixtures/surface-decoration/marquee-glyph-frame.yaml").read_text())
    patch = fixture["themePatch"]
    parts = sr.bundle()
    for key in ("values", "roles", "colorBindings"):
        parts["theme"]["body"][key].update(patch[key])
    parts["scheme"]["body"]["categories"].update(fixture["schemePatch"]["categories"])
    resolved = resolve_theme(parts["theme"], parts["scheme"], scheme_content_identity="sha256:test")
    body = resolved["body"]
    panel = body["roles"]["region-frame-marquee"]
    glyph = body["roles"]["frame-glyph-marquee"]
    assert body["values"][panel["fill"]]["value"] == "#181818"
    assert body["values"][glyph["fill"]]["value"] == "#FFDA63"
    assert body["values"][glyph["stroke"]]["value"] == "#C99824"
