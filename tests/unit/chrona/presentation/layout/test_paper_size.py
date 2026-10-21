from __future__ import annotations

import pytest

from chrona.presentation.layout.paper_size import PAGE_SIZE_NAMES, viewport_for_page_size


@pytest.mark.parametrize("page_size", PAGE_SIZE_NAMES)
def test_named_page_sizes_close_positive_integer_context_dimensions(page_size):
    width, height = viewport_for_page_size(page_size)
    assert width > 0 and height > 0
    assert isinstance(width, int) and isinstance(height, int)


@pytest.mark.parametrize("page_size,expected", [
    ("a3-portrait", (1123, 1587)),
    ("a4-portrait", (794, 1123)),
    ("a5-portrait", (559, 794)),
    ("letter-portrait", (816, 1056)),
    ("legal-portrait", (816, 1344)),
])
def test_portrait_dimensions_follow_css_physical_unit_relations(page_size, expected):
    assert viewport_for_page_size(page_size) == expected


@pytest.mark.parametrize("name,width_mm,height_mm", [("a3", 297, 420), ("a4", 210, 297), ("a5", 148, 210)])
def test_iso_page_conversion_rounds_only_at_the_context_boundary(name, width_mm, height_mm):
    width, height = viewport_for_page_size(f"{name}-portrait")
    assert abs(width - width_mm * 96 / 25.4) <= 0.5
    assert abs(height - height_mm * 96 / 25.4) <= 0.5


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
