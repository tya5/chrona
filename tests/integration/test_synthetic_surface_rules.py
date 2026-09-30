"""#575: core surface rules proven on synthetic Projects, with no `examples/` input.

The HALCYON tests that touch the same rules stay as evidence. These tests are
the gate: each renders a small project built in `tests/support/synthetic_review.py`
through a packaged preset bundle, so a corpus edit cannot change what they prove.
"""
from __future__ import annotations

import pytest

import chrona.presentation.scene.v05_builder as builder
from tests.support import synthetic_review as sr


def _parts(*, distribution: str = "pack") -> dict:
    parts = sr.bundle()
    parts["view"] = sr.lane_view(parts["view"])
    parts["layout"]["reviewSurface"]["rowDistribution"] = distribution
    return parts


def _suppressed_names(scene) -> list[str]:
    return [item for item in scene.diagnostics if item.startswith("W_LAYOUT_LABEL_SUPPRESSED:member-label:")]


def _overlaps(a, b) -> bool:
    return (a[0] < b[0] + b[2] and b[0] < a[0] + a[2] and a[1] < b[1] + b[3] and b[1] < a[1] + a[3])


# --- (a) a fixed review host reports a typed shortage and completes visibly ---------------------------------


def _density(tmp_path, block: int):
    parts = _parts()
    sr.fix_block(parts, "review", block)
    rendered = sr.render(tmp_path, sr.bunched_project(), presentation=parts)
    return rendered.surface, [w for w in rendered.surface.fit_warnings if w.code == "W_LAYOUT_ROW_DENSITY"]


def test_fixed_host_with_more_lane_rows_than_fit_reports_row_density_and_completes_visibly(tmp_path):
    surface, warnings = _density(tmp_path, 300)

    assert len(surface.rows) == 24
    last = max(surface.rows, key=lambda row: row.bounds[1] + row.bounds[3])
    row_bottom = last.bounds[1] + last.bounds[3]
    timeline = next(slot for slot in surface.slots if slot.source == "timeline")
    slot_bottom = timeline.bounds[1] + timeline.bounds[3]
    assert row_bottom > slot_bottom, "the fixture must overflow its fixed host"

    # Required is the row's own height; available is what is left of the host below the row's top.
    for row in surface.rows:
        shortage = next((item for item in warnings if item.placement_id == f"row:{row.row_id}"), None)
        if row.bounds[1] + row.bounds[3] <= slot_bottom + 0.01:
            assert shortage is None
            continue
        assert shortage is not None and shortage.behaviour == "visible-overflow"
        assert shortage.required_block == pytest.approx(row.bounds[3])
        assert shortage.available_block == pytest.approx(max(0.0, slot_bottom - row.bounds[1]))
        assert shortage.required_block > shortage.available_block
    assert any(item.placement_id == f"row:{last.row_id}" for item in warnings)
    # The host is not expanded: the shortage is reported for every row that ends past its end,
    # and none for a row that fits.
    assert {item.placement_id for item in warnings} == {
        f"row:{row.row_id}" for row in surface.rows if row.bounds[1] + row.bounds[3] > slot_bottom + 0.01}
    assert 0 < len(warnings) < len(surface.rows)
    # Natural visible fallback: every row and primitive is inside the completed canvas.
    canvas = surface.canvas_bounds
    for bounds in [row.bounds for row in surface.rows] + [item.bounds for item in surface.primitives]:
        assert canvas[0] <= bounds[0] and bounds[0] + bounds[2] <= canvas[0] + canvas[2] + 0.01
        assert canvas[1] <= bounds[1] and bounds[1] + bounds[3] <= canvas[1] + canvas[3] + 0.01


def test_a_fixed_host_that_fits_reports_no_row_density(tmp_path):
    surface, warnings = _density(tmp_path, 1800)
    timeline = next(slot for slot in surface.slots if slot.source == "timeline")
    assert max(row.bounds[1] + row.bounds[3] for row in surface.rows) <= timeline.bounds[1] + timeline.bounds[3]
    assert warnings == []


# --- (b) fill lanes count every packed name as shown or suppressed ------------------------------------------


def test_fill_lanes_count_every_packed_name_as_shown_or_suppressed(tmp_path):
    parts = _parts(distribution="fill")
    source = sr.bunched_project()
    sr.add_notes(source, parts["view"], ["g0-t2", "g1-t3", "g2-t1"],
                 [sr.candidate("plot-near", connector="leader"), sr.candidate("plot-no-tail", connector="none")])
    rendered = sr.render(tmp_path, source, presentation=parts)
    surface = rendered.surface

    packed = len(surface.lane_members)
    names = [item for item in surface.primitives if item.purpose == "member-label"]
    suppressed = _suppressed_names(rendered.scene)
    assert packed == 24
    assert packed == len(names) + len(suppressed)
    assert names and suppressed, "the fixture must both show and suppress names"
    assert len(suppressed) == len(set(suppressed))
    assert f"I_LAYOUT_PLOT_LABELS_SUPPRESSED:surface=table-timeline;count={len(suppressed)}" in rendered.scene.diagnostics
    assert not [item for item in surface.primitives if item.purpose == "member-label-leader"]
    boxes = [item for item in surface.primitives if item.scene_id.startswith("annotation-box:")]
    assert len(boxes) == 3
    for box in boxes:
        assert not [name for name in names if _overlaps(box.bounds, name.bounds)], box.scene_id


# --- (c) a member label stays within its row band ------------------------------------------------------------


def test_member_labels_stay_in_their_row_band_at_the_bar_end_or_start(tmp_path):
    # The fixed review host is shorter than its three lane rows, so the last row reaches past the
    # timeline slot: the band that bounds a name is the row's own extent, not the slot's.
    parts = _parts(distribution="fill")
    sr.fix_block(parts, "review", 310)
    rendered = sr.render(tmp_path, sr.chain_project(), presentation=parts)
    surface = rendered.surface
    timeline = next(slot for slot in surface.slots if slot.source == "timeline")
    assert max(row.bounds[1] + row.bounds[3] for row in surface.rows) > timeline.bounds[1] + timeline.bounds[3]
    rows = {row.row_id: row for row in surface.rows}
    marks = {(item.lane_row_id, item.lane_member_id): item for item in surface.primitives
             if item.purpose == "planned"}
    names = [item for item in surface.primitives if item.purpose == "member-label"]
    suppressed = _suppressed_names(rendered.scene)

    assert len(surface.lane_members) == 12 == len(names) + len(suppressed)
    assert names, "the fixture must show names"
    for name in names:
        row, host = rows[name.lane_row_id], marks[(name.lane_row_id, name.lane_member_id)]
        assert row.bounds[1] - 0.01 <= name.bounds[1]
        assert name.bounds[1] + name.bounds[3] <= row.bounds[1] + row.bounds[3] + 0.01, name.scene_id
        assert (name.bounds[0] >= host.bounds[0] + host.bounds[2] - 0.5
                or name.bounds[0] + name.bounds[2] <= host.bounds[0] + 0.5), name.scene_id
    # Default behaviour of this fixture: every name fits beside its own bar, none is counted suppressed.
    assert suppressed == []


# --- (d) a crowded plot falls back to a declared rail with a named diagnostic -------------------------------


def _annotated(tmp_path, monkeypatch, *, plot_positions: int, second_positions: int):
    """Three notes anchored at bar ends, each offering two plot candidates and then a declared rail.

    A note box centred on a bar end lands on that bar's own visible name, so a candidate that
    may examine only one position is crowded out; one that may examine 1024 positions is not.
    """
    compositions = []
    original = builder.compose_surface_layout

    def capture(request):
        result = original(request)
        compositions.append(result)
        return result

    monkeypatch.setattr(builder, "compose_surface_layout", capture)
    parts = _parts(distribution="fill")
    sr.with_balloon_notes(parts)
    sr.with_note_rail(parts)
    source = sr.chain_project()
    rail = sr.candidate("rail-after-crowding", region={"kind": "slot", "source": "annotations"},
                        search_kind="row-aligned", connector="leader")
    sr.add_notes(source, parts["view"], ["g0-t1", "g1-t2", "g2-t1"],
                 [sr.candidate("plot-near", max_positions=plot_positions, connector="tail"),
                  sr.candidate("plot-no-tail", max_positions=second_positions, connector="none"), rail],
                 endpoint="finish")
    rendered = sr.render(tmp_path, source, presentation=parts)
    decisions = {item.source_ref: item for item in compositions[0].placement.decisions
                 if item.decision_id.startswith("annotation:")}
    return rendered, decisions


def test_crowded_plot_selects_the_declared_rail_with_a_named_diagnostic(tmp_path, monkeypatch):
    rendered, decisions = _annotated(tmp_path, monkeypatch, plot_positions=1, second_positions=1)

    assert set(decisions) == {"note-0", "note-1", "note-2"}
    rail = {note for note, decision in decisions.items() if decision.selected_rung == "rail-after-crowding"}
    assert rail == set(decisions)
    for note in rail:
        assert decisions[note].search_count > 1
        assert f"W_LAYOUT_ANNOTATION_CANDIDATE_FALLBACK:{note}:rail-after-crowding" in rendered.scene.diagnostics
        assert any(item.scene_id == f"annotation-box:{note}" for item in rendered.surface.primitives)


def test_a_plot_with_room_never_selects_the_rail(tmp_path, monkeypatch):
    rendered, decisions = _annotated(tmp_path, monkeypatch, plot_positions=1, second_positions=1024)

    assert {decision.selected_rung for decision in decisions.values()} == {"plot-no-tail"}
    assert not [item for item in rendered.scene.diagnostics if item.endswith(":rail-after-crowding")]
    assert all(f"W_LAYOUT_ANNOTATION_CANDIDATE_FALLBACK:{note}:plot-no-tail" in rendered.scene.diagnostics
               for note in decisions)
