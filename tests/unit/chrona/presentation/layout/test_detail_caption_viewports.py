"""Detail captions travel with whole native panels, including natural stacking/growth."""
from dataclasses import replace
from datetime import date
from decimal import Decimal

import pytest

from chrona.presentation.layout.model import LayoutDecision, Rect, SlotHeading
from chrona.presentation.layout.sources import MeasuredSources, SourceInput
from chrona.presentation.layout.surface_composer import compose_surface_layout
from chrona.presentation.layout.surface_quality import SurfaceLayoutRequest
from chrona.presentation.model.presentation_contract import normalize_presentation_input
from chrona.presentation.model.projection import ReviewItem, ReviewProjection
from chrona.presentation.model.theme_tokens import ThemeTokenView
from tests.unit.chrona.presentation.scene.test_v05_builder import (
    _Font, _manifest, _theme, _title_measurement, surface_content,
)


def _compose(*, headed=True, description="Description"):
    item = ReviewItem("a", "Activity", "span", {"start": date(2026, 1, 1), "end": date(2026, 1, 2)},
                      None, None, ())
    projection = ReviewProjection((item,), (date(2026, 1, 1), date(2026, 1, 3)), (), ())
    content = surface_content(group_details=(("team", "Team", description),),
                              milestones=(("gate", "Gate", date(2026, 1, 2)),))
    manifest = _manifest("title", "table", "timeline", "timeline-axis")
    panel = Rect(Decimal(0), Decimal(1050), Decimal(250), Decimal(70))
    manifest = replace(manifest, viewport=Rect(Decimal(0), Decimal(0), Decimal(1000), Decimal(1400)),
        decisions=manifest.decisions + tuple(LayoutDecision(source, "slot", panel, source,
            heading=SlotHeading(label) if headed else None)
            for source, label in (("group-details", "Details"), ("milestones", "Milestones"))))
    measured = MeasuredSources({"title": _title_measurement()}, {"title": SourceInput(("Plan",))}, {
        "text.body.size": Decimal(14), "text.body.lineHeight": Decimal("1.4"),
        "timeline.row.minBlockSize": Decimal(40), "timeline.row.paddingBlock": Decimal(8),
        "timeline.mark.blockSize": Decimal(8)})
    theme = _theme()
    theme["body"]["roles"]["slot-heading"] = dict(theme["body"]["roles"]["text"])
    return compose_surface_layout(SurfaceLayoutRequest(
        projection=projection, presentation_contract=normalize_presentation_input(content),
        surface_content=content, layout_manifest=manifest, measured_sources=measured,
        theme_tokens=ThemeTokenView(theme), font_metrics=_Font(), capabilities={"svg": True})).placement


@pytest.mark.parametrize("description", ["Description", "Long description " * 40])
def test_captions_and_detail_content_complete_in_nonoverlapping_whole_panels(description):
    placed = _compose(description=description)
    slots = {slot.source_ref: slot for slot in placed.slots}
    texts = {text.placement_id: text for text in placed.text}
    for source, identifier in (("group-details", "group-detail:team"), ("milestones", "milestone:gate")):
        caption, content = texts[f"slot-heading:{source}"], texts[identifier]
        assert caption.bounds.block == slots[source].bounds.block
        assert caption.bounds.block + caption.bounds.block_size < content.bounds.block
        assert content.bounds.block + content.bounds.block_size <= (
            slots[source].bounds.block + slots[source].bounds.block_size)
    group, milestone = slots["group-details"], slots["milestones"]
    assert group.bounds.block + group.bounds.block_size <= milestone.bounds.block


def test_native_panel_growth_without_captions_keeps_the_existing_stack_rule():
    placed = _compose(headed=False, description="Long description " * 40)
    slots = {slot.source_ref: slot for slot in placed.slots}
    assert not any(text.placement_id.startswith("slot-heading:") for text in placed.text)
    assert slots["group-details"].bounds.block == 1050
    assert slots["milestones"].bounds.block == (
        slots["group-details"].bounds.block + slots["group-details"].bounds.block_size)
