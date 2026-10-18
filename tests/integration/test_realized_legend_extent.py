"""Candidate-only legend height must not survive final realization (#1679)."""
from copy import deepcopy
from dataclasses import replace

from chrona.presentation.layout import surface_composer
from tests.integration.test_realized_legends import ACTUAL, _parts, _render, _source


def _without_legend_primitives(rendered):
    return tuple(item for item in rendered.surface.primitives
                 if item.slot_id != "legend")


def _legend_slot(rendered):
    return next(slot for slot in rendered.surface.slots if slot.source == "legend")


def test_filtered_candidate_growth_is_released_from_completed_canvas_without_chart_movement(
        tmp_path, monkeypatch):
    actual = deepcopy(ACTUAL)
    for observation in actual["body"]["observations"]:
        if observation["projectObjectId"] in {"track", "behind"}:
            observation["actual"].update(start="2026-02-22", finish="2026-02-24")
        elif observation["projectObjectId"] == "gate":
            observation["actual"]["at"] = "2026-02-22"
    baseline = _render(tmp_path / "baseline", _source(), actual=actual, parts=_parts())
    original_reservation = surface_composer.reserve_potential_legend
    initial_batches = []

    def inflated_potential_batch(request, legend, slots, headings, metric_values, metric_for):
        batch, completed_slots = original_reservation(
            request, legend, slots, headings, metric_values, metric_for)
        # Simulate conservative space reserved for possible keys that final
        # placement visibility will remove. Keep the allocation itself fixed.
        initial_batches.append((batch, len(request.surface_content.legend_entries)))
        inflated = replace(batch, slot=replace(batch.slot, bounds=replace(
            batch.slot.bounds, block_size=batch.slot.bounds.block_size + 10000)))
        return inflated, tuple(replace(slot, bounds=replace(
            slot.bounds, block_size=slot.bounds.block_size + 10000))
            if slot.source_ref == "legend" else slot for slot in completed_slots)

    monkeypatch.setattr(surface_composer, "reserve_potential_legend", inflated_potential_batch)
    realized = _render(tmp_path / "inflated", _source(), actual=actual, parts=_parts())

    assert len(initial_batches) == 1
    potential, potential_key_count = initial_batches[0]
    assert potential.slot.bounds.block_size > potential.allocated_slot.bounds.block_size
    realized_key_count = len(tuple(item for item in realized.surface.primitives
                                   if item.purpose == "legend-swatch"))
    assert potential_key_count > realized_key_count
    assert realized_key_count == len(tuple(item for item in baseline.surface.primitives
                                           if item.purpose == "legend-swatch"))

    # Only the conservative candidate slot was changed. Final key geometry,
    # every non-legend placement, and all other completed slots stay identical.
    assert _without_legend_primitives(realized) == _without_legend_primitives(baseline)
    assert _legend_slot(realized) == _legend_slot(baseline)
    assert tuple(slot for slot in realized.surface.slots if slot.source != "legend") == tuple(
        slot for slot in baseline.surface.slots if slot.source != "legend")
    assert realized.surface.canvas_bounds == baseline.surface.canvas_bounds
    assert realized.surface.canvas_warning == baseline.surface.canvas_warning is None
    assert not any(item.payload["code"] == "W_LAYOUT_CANVAS_EXCEEDS_VIEWPORT"
                   for item in realized.warning_records)
