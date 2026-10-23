"""The Theme gap is resolved once and shared by member-label geometry."""
from decimal import Decimal

import pytest

from chrona.presentation.layout.label_footprint_measurement import member_label_gap
from chrona.presentation.layout.model import LayoutError
from chrona.presentation.layout.sources import resolve_theme_metrics
from tests.unit.chrona.presentation.layout.test_sources import theme


@pytest.mark.parametrize(("font_size", "expected"), [(2, 1), (10, 2.5), (20, 5)])
def test_unbound_gap_retains_existing_font_relative_default(font_size, expected):
    assert member_label_gap(font_size) == expected
    assert member_label_gap(font_size, {}) == expected


@pytest.mark.parametrize("value", [0, 0.5, 8])
def test_authored_gap_replaces_the_font_relative_default(value):
    document = theme()
    document["body"]["metrics"]["timeline.mark.labelGap"] = "member-gap"
    document["body"]["values"]["member-gap"] = {"type": "number", "value": value}
    metrics = resolve_theme_metrics(document)
    assert metrics["timeline.mark.labelGap"] == Decimal(str(value))
    assert member_label_gap(20, metrics) == value


@pytest.mark.parametrize("value", [-1, "NaN", "Infinity", "bad"])
def test_invalid_gap_is_refused_by_the_existing_metric_resolver(value):
    document = theme()
    document["body"]["metrics"]["timeline.mark.labelGap"] = "member-gap"
    document["body"]["values"]["member-gap"] = {"type": "number", "value": value}
    with pytest.raises(LayoutError) as caught:
        resolve_theme_metrics(document)
    assert caught.value.diagnostic_id == "E_LAYOUT_TOKEN_TYPE"
    assert caught.value.path == "/body/metrics/timeline.mark.labelGap"
