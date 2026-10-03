"""#1049: the `annotationContainer.border` token reader (the Theme schema also rejects these) and the strip geometry."""
from __future__ import annotations

from decimal import Decimal

import pytest

from chrona.presentation.layout.annotation_border import NO_BORDER, resolve_border, side_strip
from chrona.presentation.model.theme_tokens import ThemeTokenError, ThemeTokenView
from tests.unit.chrona.presentation.model.test_theme_tokens import _theme_with_annotation_container


def _read(**extra):
    value = {"outline": "rectangle", "cornerRadius": 0, **extra}
    return ThemeTokenView(_theme_with_annotation_container(value)).annotation_container("annotation")


def test_no_border_is_none_and_resolves_to_the_empty_border():
    container = _read()
    assert container.border is None and resolve_border(container.border) is NO_BORDER and NO_BORDER.empty


def test_a_border_reads_each_side_with_its_width_and_paint():
    container = _read(border={"start": {"width": 3, "paint": "kind"}, "top": {"width": 1.5}, "end": {"width": 0}})
    assert container.border["start"].width == Decimal("3") and container.border["start"].paint == "kind"
    assert container.border["top"].paint == "ink"  # the default
    border = resolve_border(container.border)
    assert border.insets == (1.5, 0.0, 0.0, 3.0)  # top, right (end), bottom, left (start)
    assert border.paints == {"start": "kind", "top": "ink"}  # a width-0 side has no paint
    assert not border.empty


def test_a_border_is_admitted_with_a_corner_radius():
    container = _read(cornerRadius=0.25, border={"start": {"width": 3, "paint": "kind"}})
    assert container.corner_radius == Decimal("0.25") and container.border["start"].width == Decimal("3")


@pytest.mark.parametrize("extra", [
    {"outline": "balloon", "cornerRadius": 0.2, "tailBaseEm": 0.6, "border": {"start": {"width": 3}}},
    {"outline": "image", "image": "chrona:frame", "sliceInsetsEm": {"top": 1, "right": 1, "bottom": 1, "left": 1},
     "contentInsetEm": {"top": 1, "right": 1, "bottom": 1, "left": 1}, "border": {"start": {"width": 3}}},
    {"border": {}}, {"border": []}, {"border": {"middle": {"width": 1}}},
    {"border": {"start": {}}}, {"border": {"start": {"width": -1}}}, {"border": {"start": {"width": True}}},
    {"border": {"start": {"width": 1, "paint": "red"}}}, {"border": {"start": {"width": 1, "style": "dashed"}}},
])
def test_an_unsupported_or_malformed_border_names_its_property(extra):
    value = {"outline": "rectangle", "cornerRadius": 0, **extra}
    with pytest.raises(ThemeTokenError) as raised:
        ThemeTokenView(_theme_with_annotation_container(value)).annotation_container("annotation")
    assert raised.value.diagnostic_id == "E_THEME_TOKEN_TYPE"
    assert "/annotationContainer/border" in raised.value.path


@pytest.mark.parametrize("side,expected", [
    ("start", (10, 20, 4, 50)), ("end", (106, 20, 4, 50)), ("top", (10, 20, 100, 4)), ("bottom", (10, 66, 100, 4)),
])
def test_a_strip_stands_on_its_side_at_full_length(side, expected):
    assert side_strip(side, 4, (10, 20, 100, 50)) == expected
