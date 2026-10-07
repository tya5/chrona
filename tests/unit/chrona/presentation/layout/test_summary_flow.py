from decimal import Decimal
from types import SimpleNamespace

import pytest

from chrona.presentation.layout.model import Rect
from chrona.presentation.layout.sources import SourceInput, SourceTextRun, measure_sources
from chrona.presentation.layout.surface_content import place_summary
from chrona.presentation.layout.surface_quality import SlotPlacement, SurfaceLayoutRequest
from chrona.presentation.model.surface_content import SummaryContent, SummaryPanel, SummaryTextRun
from chrona.presentation.model.theme_tokens import ThemeTokenView
from tests.unit.chrona.presentation.layout.test_sources import theme


def test_summary_uses_effective_transformed_numeric_scaled_widths_and_closed_baselines():
    class Metrics:
        content_identity = "sha256:summary"
        def ensure_numeric_spacing(self, value):
            assert value in {"tabular", "proportional"}
        def width(self, value, size, *, letter_spacing=0, numeric_spacing="proportional"):
            units = sum(3 if c.isdigit() and numeric_spacing == "tabular"
                        else 2 if c.isupper() else 1 for c in value)
            return units * size + max(0, len(value) - 1) * letter_spacing
        def baseline(self, top, size, line_height):
            return top + size * 2  # A font baseline outside its nominal line pitch.

    resolved = theme()
    body = resolved["body"]
    body["values"]["text-transform"]["value"] = "uppercase"
    body["values"]["numeric-spacing"]["value"] = "tabular"
    for role, base, size, gap in (("summary-caption", "summary", 14, 7),
                                 ("metric", "metric", 34, 11),
                                 ("summary-unit", "summary", 10, 999)):
        body["values"][role + ".size"] = {"type": "number", "value": size}
        body["values"][role + ".scale"] = {"type": "number", "value": 0.8}
        body["values"][role + ".gap"] = {"type": "number", "value": gap}
        body["roles"][role] = body["roles"][base] | {
            "fontSize": role + ".size", "horizontalScale": role + ".scale", "inlineGap": role + ".gap"}
    content = SummaryContent((SummaryPanel("key", (
        SummaryTextRun("summary:key", "key", "ab", "summary-caption", "summaryCaption"),
        SummaryTextRun("summary:key:m:value", "key", "11", "metric", "summaryFigureValue"),
        SummaryTextRun("summary:key:m:caption", "key", "days", "summary-unit", "summaryUnit"),
    ), arrangement="inline"),))
    source = SourceInput(runs=tuple(SourceTextRun(r.content, r.typography_role, r.placement_id)
                                    for r in content.runs), summary=content)
    measured = measure_sources({"summary": source}, resolved, font_metrics=Metrics())
    closure = measured.summary_flows["summary"]
    slot = SlotPlacement("summary", "summary", Rect(Decimal(0), Decimal(0),
                         measured.measurements["summary"].preferred_inline, closure.block_size))
    request = SurfaceLayoutRequest(surface_content=SimpleNamespace(summary=content),
                                    measured_sources=measured, theme_tokens=ThemeTokenView(resolved),
                                    font_metrics=Metrics())
    placed = place_summary(request, slot)
    assert [r.content for r in placed] == ["AB", "11", "DAYS"]
    assert [r.source_content for r in placed] == ["ab", "11", "days"]
    assert {r.baseline[1] for r in placed} == {68}
    for p, m in zip(placed, measured.run_measurements["summary"]):
        assert float(p.bounds.inline_size) == pytest.approx(float(m.inline_size))
        assert p.bounds.block >= 0
        assert p.bounds.block + p.bounds.block_size <= closure.block_size
    assert placed[1].baseline[0] == pytest.approx(float(placed[0].bounds.inline_size) + 7)
    assert placed[2].baseline[0] == pytest.approx(placed[1].baseline[0] + float(placed[1].bounds.inline_size) + 11)
    assert float(closure.inline_size) == pytest.approx(placed[-1].baseline[0] + float(placed[-1].bounds.inline_size))
