from decimal import Decimal
from dataclasses import replace

from chrona.presentation.layout.model import Rect
from chrona.presentation.layout.sources import SourceInput, SourceTextRun, measure_sources
from chrona.presentation.layout.model import Measurement
from chrona.presentation.layout.surface_heading import place_heading
from chrona.presentation.layout.surface_quality import SlotPlacement, SurfaceLayoutRequest
from chrona.presentation.model.theme_tokens import ThemeTokenView
from tests.unit.chrona.presentation.layout.test_sources import theme


def test_block_heading_projects_transformed_measurement_and_keeps_source_text():
    class Metrics:
        content_identity = "sha256:case-sensitive"
        def width(self, value, size, **kwargs):
            return sum(2 if character.isupper() else 1 for character in value) * size
        def baseline(self, top, size, line_height):
            return top + size

    resolved = theme()
    resolved["body"]["values"]["text-transform"]["value"] = "uppercase"
    measured = measure_sources({"title": SourceInput(
        runs=(SourceTextRun("ab", "heading", "title"),), run_flow="block")},
        resolved, font_metrics=Metrics())
    request = SurfaceLayoutRequest(theme_tokens=ThemeTokenView(resolved), font_metrics=Metrics())
    slot = SlotPlacement("title", "title", Rect(Decimal(0), Decimal(0), Decimal(200), Decimal(60)))
    placed, = place_heading(request, slot, measured)
    assert placed.content == "AB"
    assert placed.source_content == "ab"
    assert placed.bounds.inline_size == measured.run_measurements["title"][0].inline_size == Decimal(136)


def test_native_title_baseline_uses_original_run_measurement_not_caption_reserve():
    class Metrics:
        content_identity = "sha256:native-title"
        def width(self, value, size, **kwargs): return len(value) * size / 2
        def baseline(self, top, size, line_height): return top + size

    resolved = theme()
    measured = measure_sources({"title": SourceInput(("A title",), typography_role="heading")},
                               resolved, font_metrics=Metrics())
    original = measured.measurements["title"]
    reserved = Measurement(original.min_inline, original.preferred_inline, original.max_inline,
                            original.min_block + 30, original.preferred_block + 30, original.max_block + 30,
                            original.first_baseline + 30, original.last_baseline + 30)
    measured = replace(measured, measurements={**measured.measurements, "title": reserved})
    request = SurfaceLayoutRequest(theme_tokens=ThemeTokenView(resolved), font_metrics=Metrics())
    slot = SlotPlacement("title", "title", Rect(Decimal(0), Decimal(30), Decimal(200), Decimal(60)))
    placed, = place_heading(request, slot, measured)
    assert placed.baseline[1] == float(slot.bounds.block + measured.run_measurements["title"][0].baseline)
