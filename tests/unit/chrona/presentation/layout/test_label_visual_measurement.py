from decimal import Decimal
from types import SimpleNamespace

import pytest

from chrona.presentation.layout.label_visual_measurement import measure_label_visual_run
from chrona.presentation.layout.model import LayoutError
from chrona.presentation.layout.surface_quality import VisualRequest
from chrona.presentation.model.font_metrics import FontMetricsCatalog, FontMetricsError


class _Metrics:
    def __init__(self):
        self.selected = None

    def select(self, family, weight):
        self.selected = (family, weight)
        return self

    def width(self, content, size, **kwargs):
        return len(content) * size + kwargs.get("letter_spacing", 0) * len(content)


class _Theme:
    def __init__(self, *, scale=Decimal("0.5"), gap=Decimal("0.2"), broken=False):
        self.scale, self.gap, self.broken = scale, gap, broken

    def text_treatment(self, _role):
        return SimpleNamespace(family="Test Sans", weight=500, font_size=Decimal(10),
                               line_height=Decimal("1.25"), letter_spacing=Decimal("0.5"),
                               transform="uppercase", numeric_spacing="proportional", horizontal_scale=Decimal(1))

    def icon_ratios(self, _role):
        if self.broken:
            raise ValueError("bad icon ratio")
        return self.scale, self.gap


def _visual(side, *, kind="plot-label", selector=None, ref="icon", source="/body/visuals/0"):
    return VisualRequest(kind, tuple((selector or {"id": "task"}).items()), ref=ref,
                         side=side, source_ref=source)


def _icon():
    return SimpleNamespace(icon_id="icon", kind="vector", content_identity="sha256:icon",
                           viewport=(20, 10), payload=(), alternative="task icon")


def test_measurement_reserves_exact_leading_trailing_and_both_advances():
    metrics = _Metrics()
    requests = (_visual("leading"), _visual("trailing", source="/body/visuals/1"))
    measured = measure_label_visual_run(
        "member-label:task:row-1", "Task +2d", "text", visual_requests=requests,
        icon_assets={"icon": _icon()}, theme_tokens=_Theme(), font_metrics=metrics,
    )

    assert (measured.leading_advance, measured.trailing_advance) == (12, 12)
    assert measured.text_width == len("TASK +2D") * 10 + len("TASK +2D") * 0.5
    assert measured.text_block_size == 12.5
    assert measured.required_inline_size == measured.leading_advance + measured.text_width + measured.trailing_advance
    assert metrics.selected == ("Test Sans", 500)
    assert tuple(item[0].side for item in measured.visuals) == ("leading", "trailing")


def test_measurement_matches_canonical_plot_label_target_to_projection_instance():
    measured = measure_label_visual_run(
        "member-label:task:review-row:attached-item", "Task", "text",
        visual_requests=(_visual("leading", selector={"id": "task"}),),
        icon_assets={"icon": _icon()}, theme_tokens=_Theme(), font_metrics=_Metrics(),
    )
    assert measured.leading_advance == 12
    assert measured.trailing_advance == 0


def test_measurement_rejects_duplicate_side_with_existing_diagnostic():
    with pytest.raises(LayoutError, match="E_LAYOUT_VISUAL_DUPLICATE"):
        measure_label_visual_run(
            "member-label:task", "Task +2d", "text",
            visual_requests=(_visual("leading"), _visual("leading", source="/body/visuals/1")),
            icon_assets={"icon": _icon()}, theme_tokens=_Theme(), font_metrics=_Metrics(),
        )


def test_measurement_rejects_unknown_target_and_missing_icon_asset():
    with pytest.raises(LayoutError, match="E_LAYOUT_VISUAL_TARGET"):
        measure_label_visual_run(
            "member-label:task", "Task", "text",
            visual_requests=(_visual("leading", kind="unknown-target"),),
            icon_assets={"icon": _icon()}, theme_tokens=_Theme(), font_metrics=_Metrics(),
        )
    with pytest.raises(LayoutError, match="E_ICON_NAME_UNKNOWN"):
        measure_label_visual_run(
            "member-label:task", "Task", "text", visual_requests=(_visual("leading"),),
            icon_assets={}, theme_tokens=_Theme(), font_metrics=_Metrics(),
        )


def test_measurement_preserves_theme_ratio_diagnostic():
    with pytest.raises(LayoutError, match="E_THEME_ICON_RATIO"):
        measure_label_visual_run(
            "member-label:task", "Task", "text", visual_requests=(_visual("leading"),),
            icon_assets={"icon": _icon()}, theme_tokens=_Theme(broken=True), font_metrics=_Metrics(),
        )


def test_measurement_preserves_missing_font_metric_diagnostic():
    with pytest.raises(FontMetricsError, match="E_FONT_METRICS_UNAVAILABLE"):
        measure_label_visual_run(
            "member-label:task", "Task +2d", "text", visual_requests=(),
            icon_assets={}, theme_tokens=_Theme(), font_metrics=FontMetricsCatalog({}),
        )
