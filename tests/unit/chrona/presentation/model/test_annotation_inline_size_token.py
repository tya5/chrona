"""#1051: the `annotationContainer.inlineSize` and `maxInlineEm` token reader (the schema also rejects these)."""
from __future__ import annotations

from decimal import Decimal

import pytest

from chrona.presentation.model.theme_tokens import ThemeTokenError, ThemeTokenView
from tests.unit.chrona.presentation.model.test_theme_tokens import _theme_with_annotation_container


def _read(**extra):
    value = {"outline": "rectangle", "cornerRadius": 0, **extra}
    return ThemeTokenView(_theme_with_annotation_container(value)).annotation_container("annotation")


def test_the_default_is_content_with_no_maximum():
    container = _read()
    assert container.inline_size == "content" and container.max_inline_em is None


def test_fill_and_a_maximum_are_read_for_every_outline():
    container = _read(inlineSize="fill", maxInlineEm=24.5)
    assert container.inline_size == "fill" and container.max_inline_em == Decimal("24.5")
    balloon = ThemeTokenView(_theme_with_annotation_container(
        {"outline": "balloon", "cornerRadius": 0.2, "tailBaseEm": 0.6, "inlineSize": "fill"})).annotation_container("annotation")
    assert balloon.inline_size == "fill"
    image = ThemeTokenView(_theme_with_annotation_container(
        {"outline": "image", "image": "chrona:frame", "cornerRadius": 0, "inlineSize": "fill",
         "sliceInsetsEm": {"top": 1, "right": 1, "bottom": 1, "left": 1},
         "contentInsetEm": {"top": 1, "right": 1, "bottom": 1, "left": 1}})).annotation_container("annotation")
    assert image.inline_size == "fill"


@pytest.mark.parametrize("extra,suffix", [
    ({"inlineSize": "wide"}, "annotationContainer/inlineSize"),
    ({"inlineSize": 3}, "annotationContainer/inlineSize"),
    ({"maxInlineEm": 10}, "annotationContainer/maxInlineEm"),
    ({"inlineSize": "content", "maxInlineEm": 10}, "annotationContainer/maxInlineEm"),
    ({"inlineSize": "fill", "maxInlineEm": 0}, "annotationContainer/maxInlineEm"),
    ({"inlineSize": "fill", "maxInlineEm": -1}, "annotationContainer/maxInlineEm"),
    ({"inlineSize": "fill", "maxInlineEm": True}, "annotationContainer/maxInlineEm"),
    ({"inlineSize": "fill", "maxInlineEm": "wide"}, "annotationContainer/maxInlineEm"),
])
def test_a_malformed_declaration_names_its_property(extra, suffix):
    with pytest.raises(ThemeTokenError) as raised:
        _read(**extra)
    assert raised.value.path.endswith(suffix)
