"""#848: the Theme `annotationContainer.artwork` declaration and its token reader."""
from __future__ import annotations

from decimal import Decimal

import pytest

from chrona.presentation.color_scheme import resolve_theme
from chrona.presentation.model.theme_tokens import ThemeTokenError, ThemeTokenView
from tests.support import annotation_artwork as aw
from tests.support import synthetic_review as sr

ROLE = "annotation-note-box"
GLYPHS = {aw.SCROLL: {"viewport": {"inlineSize": 48, "blockSize": 64}, "parts": []}}


def _tokens(*, glyphs=None, **options):
    parts = sr.bundle()
    aw.with_artwork(parts, **options)
    resolved = resolve_theme(parts["theme"], parts["scheme"], scheme_content_identity="sha256:test")
    return ThemeTokenView(resolved, catalog_glyphs=glyphs if glyphs is not None else {})


def test_a_rectangle_container_may_declare_artwork():
    (artwork,) = _tokens().annotation_container(ROLE).artwork
    assert artwork.glyph == aw.SCROLL
    assert artwork.slice_insets == (Decimal("16.3"), Decimal("8.2"), Decimal("11.5"), Decimal("8.2"))
    assert artwork.unit_em == Decimal("0.09")


def test_a_container_without_artwork_has_none():
    assert _tokens(artwork_declared=False).annotation_container(ROLE).artwork == ()


def test_artwork_composes_with_a_tilt_cycle():
    container = _tokens(extra={"tiltDegrees": [3, -3]}).annotation_container(ROLE)
    assert container.artwork and container.tilt_degrees == (Decimal("3"), Decimal("-3"))


@pytest.mark.parametrize("options", [
    {"outline": "balloon"},                                  # a balloon's tail would pierce the frame
    {"content": None},                                       # a framed note must say where its paper is
])
def test_artwork_is_rectangle_only_and_needs_a_content_inset(options):
    with pytest.raises(ThemeTokenError) as failure:
        _tokens(**options).annotation_container(ROLE)
    assert failure.value.diagnostic_id == "E_THEME_TOKEN_TYPE"
    assert failure.value.path == "/body/roles/annotation-note-box/annotationContainer/artwork"


def test_an_image_container_cannot_take_artwork():
    parts = sr.bundle()
    theme = parts["theme"]["body"]
    theme["values"]["image-container"] = {"type": "annotationContainer", "value": {
        "outline": "image", "image": "chrona:frame", "cornerRadius": 0,
        "sliceInsetsEm": {"top": 1, "right": 1, "bottom": 1, "left": 1},
        "contentInsetEm": {"top": 1, "right": 1, "bottom": 1, "left": 1},
        "artwork": {"glyph": aw.SCROLL, "sliceInsets": aw.SCROLL_INSETS, "unitEm": 0.1}}}
    theme["roles"][ROLE]["annotationContainer"] = "image-container"
    resolved = resolve_theme(parts["theme"], parts["scheme"], scheme_content_identity="sha256:test")
    with pytest.raises(ThemeTokenError) as failure:
        ThemeTokenView(resolved).annotation_container(ROLE)
    assert failure.value.diagnostic_id == "E_THEME_TOKEN_TYPE" and failure.value.path.endswith("/artwork")


@pytest.mark.parametrize("value, suffix", [
    ({"glyph": "nope", "sliceInsets": aw.SCROLL_INSETS, "unitEm": 0.1}, "/glyph"),
    ({"glyph": "a:b:c", "sliceInsets": aw.SCROLL_INSETS, "unitEm": 0.1}, "/glyph"),
    ({"glyph": 3, "sliceInsets": aw.SCROLL_INSETS, "unitEm": 0.1}, "/glyph"),
    ({"glyph": aw.SCROLL, "sliceInsets": aw.SCROLL_INSETS, "unitEm": 0}, "/unitEm"),
    ({"glyph": aw.SCROLL, "sliceInsets": aw.SCROLL_INSETS, "unitEm": -1}, "/unitEm"),
    ({"glyph": aw.SCROLL, "sliceInsets": aw.SCROLL_INSETS, "unitEm": True}, "/unitEm"),
    ({"glyph": aw.SCROLL, "sliceInsets": aw.SCROLL_INSETS, "unitEm": "0.1"}, "/unitEm"),
    ({"glyph": aw.SCROLL, "sliceInsets": {"top": -1, "right": 0, "bottom": 0, "left": 0}, "unitEm": 0.1}, "/sliceInsets"),
    ({"glyph": aw.SCROLL, "sliceInsets": {"top": 1}, "unitEm": 0.1}, "/sliceInsets"),
    ({"glyph": aw.SCROLL, "sliceInsets": "none", "unitEm": 0.1}, "/sliceInsets"),
    ({"glyph": aw.SCROLL, "unitEm": 0.1}, ""),                                                  # a missing member
    ({"glyph": aw.SCROLL, "sliceInsets": aw.SCROLL_INSETS, "unitEm": 0.1, "fit": "cover"}, ""),  # an unknown member
])
def test_a_malformed_artwork_object_is_a_token_type_error_at_its_member(value, suffix):
    parts = sr.bundle()
    aw.with_artwork(parts)
    parts["theme"]["body"]["values"]["artwork-container"]["value"]["artwork"] = value
    resolved = resolve_theme(parts["theme"], parts["scheme"], scheme_content_identity="sha256:test")
    with pytest.raises(ThemeTokenError) as failure:
        ThemeTokenView(resolved).annotation_container(ROLE)
    assert failure.value.diagnostic_id == "E_THEME_TOKEN_TYPE"
    assert failure.value.path == f"/body/roles/annotation-note-box/annotationContainer/artwork{suffix}"


@pytest.mark.parametrize("insets", [{"top": 40, "right": 0, "bottom": 30, "left": 0},
                                    {"top": 0, "right": 30, "bottom": 0, "left": 20}])
def test_insets_larger_than_the_pinned_glyphs_viewport_are_rejected(insets):
    with pytest.raises(ThemeTokenError) as failure:
        _tokens(glyphs=GLYPHS, insets=insets).annotation_container(ROLE)
    assert failure.value.diagnostic_id == "E_THEME_TOKEN_TYPE" and failure.value.path.endswith("/artwork/sliceInsets")


def test_insets_that_exactly_fill_the_viewport_are_admitted():
    (artwork,) = _tokens(glyphs=GLYPHS, insets={"top": 32, "right": 24, "bottom": 32, "left": 24}).annotation_container(ROLE).artwork
    assert artwork is not None


def test_the_ink_role_admits_only_its_paint_and_the_fidelity_property():
    from chrona.presentation.scene.capabilities import theme_role_contract

    contract = theme_role_contract("annotation-artwork")
    assert set(contract.properties) == {"fill", "stroke", "opacity", "artworkFidelity"}
    assert set(contract.scene_kinds) == {"Symbol"}


def _list_tokens(artwork):
    parts = sr.bundle()
    aw.with_artwork(parts)
    parts["theme"]["body"]["values"]["artwork-container"]["value"]["artwork"] = artwork
    resolved = resolve_theme(parts["theme"], parts["scheme"], scheme_content_identity="sha256:test")
    return ThemeTokenView(resolved).annotation_container(ROLE).artwork


def test_list_layers_normalize_order_identity_and_default_role():
    geometry = {"glyph": aw.SCROLL, "sliceInsets": aw.SCROLL_INSETS, "unitEm": 0.09}
    layers = _list_tokens([geometry, {**geometry, "role": "annotation-artwork-rods"}])
    assert [layer.role for layer in layers] == ["annotation-artwork", "annotation-artwork-rods"]
    assert [layer.layer_index for layer in layers] == [0, 1]
    assert [layer.declaration_pointer for layer in layers] == [
        f"/body/roles/{ROLE}/annotationContainer/artwork/{index}" for index in range(2)]


@pytest.mark.parametrize("value,suffix", [
    ([], ""),
    ([None], "/0"),
    ([{"glyph": aw.SCROLL, "sliceInsets": aw.SCROLL_INSETS, "unitEm": 0}], "/0/unitEm"),
    ([{"glyph": aw.SCROLL, "sliceInsets": aw.SCROLL_INSETS, "unitEm": 0.09,
       "role": "annotation-artwork-not a slug"}], "/0/role"),
    ([{"glyph": aw.SCROLL, "sliceInsets": aw.SCROLL_INSETS, "unitEm": 0.09,
       "role": "region-frame-rods"}], "/0/role"),
])
def test_malformed_list_layer_has_indexed_token_diagnostic(value, suffix):
    with pytest.raises(ThemeTokenError) as failure:
        _list_tokens(value)
    assert failure.value.diagnostic_id == "E_THEME_TOKEN_TYPE"
    assert failure.value.path == f"/body/roles/{ROLE}/annotationContainer/artwork{suffix}"


def test_named_artwork_role_keeps_the_closed_base_capability_contract():
    from chrona.presentation.scene.capabilities import theme_role_contract

    assert theme_role_contract("annotation-artwork-rods") == theme_role_contract("annotation-artwork")
    assert theme_role_contract("annotation-artwork-not a slug") is None
