from __future__ import annotations

import pytest

from chrona.presentation.layout.paper_size import PAGE_SIZE_NAMES, viewport_for_page_size


@pytest.mark.parametrize("page_size", PAGE_SIZE_NAMES)
def test_named_page_sizes_keep_fractional_css_pixel_dimensions(page_size):
    width, height = viewport_for_page_size(page_size)
    assert width > 0 and height > 0
    assert isinstance(width, float) and isinstance(height, float)


@pytest.mark.parametrize("page_size,expected", [
    ("a3-portrait", (297 * 96 / 25.4, 420 * 96 / 25.4)),
    ("a4-portrait", (210 * 96 / 25.4, 297 * 96 / 25.4)),
    ("a5-portrait", (148 * 96 / 25.4, 210 * 96 / 25.4)),
    ("letter-portrait", (816.0, 1056.0)),
    ("legal-portrait", (816.0, 1344.0)),
])
def test_portrait_dimensions_follow_css_physical_unit_relations(page_size, expected):
    assert viewport_for_page_size(page_size) == pytest.approx(expected)


@pytest.mark.parametrize("portrait,landscape", [
    ("a3-portrait", "a3-landscape"),
    ("a4-portrait", "a4-landscape"),
    ("a5-portrait", "a5-landscape"),
    ("letter-portrait", "letter-landscape"),
    ("legal-portrait", "legal-landscape"),
])
def test_landscape_exchanges_physical_axes(portrait, landscape):
    width, height = viewport_for_page_size(portrait)
    assert viewport_for_page_size(landscape) == (height, width)


@pytest.mark.parametrize("value", ["A4", "a4", "poster-portrait", "", None])
def test_unregistered_page_sizes_are_rejected(value):
    with pytest.raises(ValueError, match="unknown named page size"):
        viewport_for_page_size(value)
