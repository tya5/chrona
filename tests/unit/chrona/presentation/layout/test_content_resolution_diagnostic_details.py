from decimal import Decimal

import pytest

from chrona.presentation.layout.engine import ContentBlockResolution, ShortContentSource


def test_shortfall_invalid_detail_names_source_and_required_allocated_blocks():
    with pytest.raises(ValueError) as error:
        ShortContentSource("summary-source-17", Decimal("83.5"), Decimal("83.5"))

    message = str(error.value)
    assert message.startswith("E_LAYOUT_CONTENT_SHORTFALL_INVALID:")
    assert "summary-source-17" in message
    assert "required_block=Decimal('83.5')" in message
    assert "allocated_block=Decimal('83.5')" in message


def test_resolution_invalid_order_detail_names_extent_and_ordered_sources():
    sources = (
        ShortContentSource("zulu-source-9", Decimal("80"), Decimal("50")),
        ShortContentSource("alpha-source-2", Decimal("70"), Decimal("40")),
    )
    with pytest.raises(ValueError) as error:
        ContentBlockResolution(137, sources)

    message = str(error.value)
    assert message.startswith("E_LAYOUT_CONTENT_RESOLUTION_INVALID:")
    assert "extent=137" in message
    assert "zulu-source-9" in message and "alpha-source-2" in message
    assert "ordered by source_id" in message


def test_resolution_duplicate_detail_names_extent_and_duplicate_source():
    sources = (
        ShortContentSource("duplicate-source-5", Decimal("60"), Decimal("30")),
        ShortContentSource("duplicate-source-5", Decimal("70"), Decimal("40")),
    )
    with pytest.raises(ValueError) as error:
        ContentBlockResolution(149, sources)

    message = str(error.value)
    assert message.startswith("E_LAYOUT_CONTENT_RESOLUTION_INVALID:")
    assert "extent=149" in message
    assert "duplicate-source-5" in message
    assert "each short source_id to occur once" in message


def test_content_resolution_detail_bounds_source_samples():
    sources = tuple(ShortContentSource(f"source-{number:03}-" + "X" * 500,
                                      Decimal(80), Decimal(50)) for number in range(40))
    with pytest.raises(ValueError) as error:
        ContentBlockResolution(-1, sources)
    assert "source_count=40" in str(error.value)
    assert "source-000-" in str(error.value)
    assert len(str(error.value)) < 1600
