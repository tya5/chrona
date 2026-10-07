"""Typed horizontal axis-tier geometry exists independently of retained interval labels (#1100)."""
from datetime import date
from decimal import Decimal

from chrona.presentation.layout.surface_axis import compose_axis
from chrona.presentation.layout.surface_base import prepare_surface_base
from chrona.presentation.layout.surface_quality import SurfaceLayoutRequest
from chrona.presentation.model.presentation_contract import normalize_presentation_input
from chrona.presentation.model.surface_content import AxisLabelIntent, AxisTier
from tests.unit.chrona.presentation.scene import test_v05_builder as base


def _axis_batch(tiers):
    item = base.ReviewItem("a", "A", "span", {"start": date(2026, 1, 1), "end": date(2027, 1, 1)}, None, None, ())
    projection = base.ReviewProjection((item,), (date(2026, 1, 1), date(2027, 1, 1)), (), ())
    measured = base.MeasuredSources({"title": base._title_measurement()}, {"title": base.SourceInput(("Plan",))},
                                    {"text.body.size": Decimal(14), "text.body.lineHeight": Decimal("1.4"),
                                     "timeline.row.minBlockSize": Decimal(40), "timeline.row.paddingBlock": Decimal(8),
                                     "timeline.mark.blockSize": Decimal(8)})
    content = base.surface_content(axis_tiers=tiers)
    value = base.build_scene_input(projection=projection, surface_content=content,
                                   layout_manifest=base._manifest("title", "table", "timeline", "timeline-axis"),
                                   resolved_theme=base._theme(), font_metrics=base._Font(), measured_sources=measured,
                                   capabilities={"svg": True})
    request = SurfaceLayoutRequest(
        projection=value.projection, presentation_contract=normalize_presentation_input(content),
        surface_content=content, layout_manifest=value.layout_manifest, measured_sources=value.measured_sources,
        theme_tokens=value.theme_tokens, font_metrics=value.font_metrics, capabilities=dict(value.capabilities))
    prepared = prepare_surface_base(request)
    return compose_axis(prepared.request, prepared)


def test_horizontal_tier_geometry_shares_the_placed_baseline_despite_thinned_months():
    tier = AxisTier("month", 1, "labels", AxisLabelIntent(
        "long-month", (), "center", "thin-with-record", "horizontal", "en-US"))

    batch = _axis_batch((tier,))

    assert len(batch.label_tiers) == 1
    geometry, = batch.label_tiers
    assert geometry.tier_index == 0
    assert geometry.bounds.inline_size > 0
    assert geometry.bounds.block_size > 0
    assert any(outcome.disposition == "thinned" for outcome in batch.tier_outcomes[0].intervals)
    placed = tuple(item for item in batch.text if item.placement_id.startswith("axis-label:0:"))
    assert placed
    assert all(item.baseline[1] == geometry.baseline_block for item in placed)
