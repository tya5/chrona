"""Native footer completion includes wrapped lines before its successor."""
from dataclasses import replace
from decimal import Decimal

import pytest

from chrona.presentation.layout.model import Rect
from chrona.presentation.layout.surface_content import complete_footer_band
from chrona.presentation.layout.surface_quality import SlotPlacement


def _slot(source, inline, block, height):
    return SlotPlacement(source, source, Rect(
        Decimal(inline), Decimal(block), Decimal(200), Decimal(height)))


@pytest.mark.parametrize("wrapped", [False, True])
@pytest.mark.parametrize("growth", [Decimal(0), Decimal(20)])
def test_successor_preserves_gap_after_every_completed_footer_line(wrapped, growth):
    panel = _slot("observations", 0, 100, 98)
    notes = _slot("notes", 0 if wrapped else 250, 214 if wrapped else 100, "39.2")
    annotation = _slot("annotations", 0, 214, 180)
    provisional = (panel, notes, annotation)
    completed = (replace(panel, bounds=replace(panel.bounds, block_size=98 + growth)),
                 notes, annotation)
    result = complete_footer_band(provisional_slots=provisional, completed_slots=completed)
    footer_end = max(slot.bounds.block + slot.bounds.block_size for slot in result[:-1])
    assert result[-1].bounds.block == footer_end + 16
    assert result[:-1] == completed[:-1]
    if not wrapped and not growth:
        assert result == provisional


def test_footer_completion_does_not_translate_an_inline_disjoint_successor():
    panel = _slot("observations", 0, 100, 98)
    notes = _slot("notes", 0, 214, "39.2")
    annotation = _slot("annotations", 500, 214, 180)
    slots = (panel, notes, annotation)
    assert complete_footer_band(provisional_slots=slots, completed_slots=slots) == slots


def test_successor_inline_overlap_can_be_with_wrapped_notes_not_the_first_panel():
    panel = _slot("observations", 0, 100, 98)
    notes = _slot("notes", 500, 214, "39.2")
    annotation = _slot("annotations", 500, 214, 180)
    slots = (panel, notes, annotation)
    result = complete_footer_band(provisional_slots=slots, completed_slots=slots)
    assert result[-1].bounds.block == Decimal("269.2")


def test_a_successor_already_placed_after_the_whole_footer_stack_is_not_translated_again():
    # #1219: the footer Flow is allocated both lines, so the manifest already puts the successor after notes + gap.
    panel = _slot("observations", 0, 100, 98)
    notes = _slot("notes", 0, 214, "39.2")
    annotation = _slot("annotations", 0, "269.2", 180)
    slots = (panel, notes, annotation)

    assert complete_footer_band(provisional_slots=slots, completed_slots=slots) == slots


def test_panel_growth_beyond_the_allocated_stack_still_moves_a_successor_placed_after_it():
    panel = _slot("observations", 0, 100, 98)
    notes = _slot("notes", 0, 214, "39.2")
    annotation = _slot("annotations", 0, "269.2", 180)
    provisional = (panel, notes, annotation)
    completed = (replace(panel, bounds=replace(panel.bounds, block_size=98 + 100)), notes, annotation)

    result = complete_footer_band(provisional_slots=provisional, completed_slots=completed)

    # The panel now ends at 298, 44.8 below the old stack end 253.2, so the successor keeps its gap: 298 + 16.
    assert result[-1].bounds.block == Decimal("314")
