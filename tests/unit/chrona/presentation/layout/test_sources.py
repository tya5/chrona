from decimal import Decimal

import pytest

from chrona.presentation.layout.model import LayoutError
from chrona.presentation.layout.sources import SourceInput, measure_sources


def theme():
    metrics = {
        "text.body.size": 14, "text.body.lineHeight": 1.4,
        "timeline.dayWidth": 12, "timeline.row.minBlockSize": 40,
        "timeline.axis.blockSize": 48, "table.column.minInlineSize": 120,
        "table.header.blockSize": 44,
    }
    return {"body": {"values": {f"metric.{i}": {"type": "number", "value": value} for i, value in enumerate(metrics.values())}, "metrics": {name: f"metric.{i}" for i, name in enumerate(metrics)}}}


def test_sources_are_measured_once_from_semantic_inputs_and_theme_metrics():
    class Metrics:
        def width(self, value, size): return len(value) * size / 2
        def baseline(self, top, size, line_height): return top + size
    measured = measure_sources({
        "title": SourceInput(("Controller Z",)),
        "table": SourceInput(item_count=5, column_count=3),
        "timeline": SourceInput(item_count=5, span_days=60),
        "timeline-axis": SourceInput(span_days=60),
    }, theme(), font_metrics=Metrics())
    assert measured.measurements["table"].preferred_inline == Decimal(360)
    assert measured.measurements["timeline"].preferred_inline == Decimal(720)
    assert measured.measurements["timeline-axis"].preferred_block == Decimal(48)
    assert measured.metric_values["text.body.size"] == Decimal(14)
    assert measured.metric_values["text.measuredAverageAdvance"] == Decimal(7)


def test_missing_unknown_and_wrong_type_metric_bindings_diagnose():
    class Metrics:
        def width(self, value, size): return len(value) * size / 2
        def baseline(self, top, size, line_height): return top + size
    value = theme(); del value["body"]["metrics"]["timeline.dayWidth"]
    with pytest.raises(LayoutError, match="E_LAYOUT_METRIC_REQUIRED"):
        measure_sources({}, value, font_metrics=Metrics())
    value = theme(); value["body"]["metrics"]["unknown.gap"] = "metric.0"
    with pytest.raises(LayoutError, match="E_LAYOUT_METRIC_UNKNOWN"):
        measure_sources({}, value, font_metrics=Metrics())
    value = theme(); value["body"]["values"]["metric.0"] = {"type": "color", "value": "#fff"}
    with pytest.raises(LayoutError, match="E_LAYOUT_TOKEN_TYPE"):
        measure_sources({}, value, font_metrics=Metrics())
