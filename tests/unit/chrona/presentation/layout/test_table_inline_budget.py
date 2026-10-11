"""Independent-budget and track-base components, not surface acceptance."""
from copy import deepcopy
from decimal import Decimal as D

import pytest

from chrona.presentation.layout.engine import (
    LayoutSizingContext, SourceInlineBudget, _Arranger, _limit_inline_base, _resolve_flexible_tracks,
    measure_natural_normal_flow_block, resolve_content_block_extent,
    resolve_source_inline_budgets, solve_layout, validate_source_inline_budgets,
)
from chrona.presentation.layout.model import LayoutError, Measurement, Rect
from chrona.presentation.layout.profile import resolve_layout_profile
from tests.unit.chrona.presentation.layout.test_intent_profile import SOURCES, fixture, theme


def slot(name="table", *, share=0.4, source="table", **extra):
    result = dict(id=name, kind="slot", source=source, inlineSize="content",
                  blockSize="content", priority="required", overflow="visible-overflow",
                  place={"inline": "start", "block": "start", "safety": "strict"})
    if share is not None:
        result["maxInlineShare"] = share
    result.update(extra)
    return result


def container(kind, children, **extra):
    result = dict(id="parent", kind=kind, children=children, inlineSize="fill",
                  blockSize="fill", gap=20, padding=10)
    if kind in {"row", "column", "flow", "grid"}:
        result.update(alignItems="start", justifyContent="start")
    if kind == "overlay":
        result.pop("gap")
    if kind == "flow":
        result["itemMinInlineSize"] = 20
    result.update(extra)
    return result


def profile(root):
    raw = fixture("layout-profile-intent-v0.2.yaml")
    raw["root"] = root
    raw["requiredThemeTokens"] = []
    return resolve_layout_profile(raw, available_sources=SOURCES, theme=theme())


def measurement(inline=2000):
    return Measurement(D(inline), D(inline), D(inline), D(10), D(10), D(10))


def probe(resolved, measurements):
    return resolve_source_inline_budgets(resolved, viewport_inline=1000,
                                       viewport_block=500, measurements=measurements)


def actual(resolved, measurements):
    arranger = _Arranger(resolved, measurements, collect_inline_budgets=True)
    arranger._record_inline_budget(resolved.profile["root"], "/root", D(1000))
    arranger.arrange(resolved.profile["root"], "/root", Rect(D(0), D(0), D(1000), D(500)))
    return arranger.source_inline_budgets


@pytest.mark.parametrize("kind,available", [("row", 960), ("column", 980),
                                          ("overlay", 980), ("flow", 980)])
def test_parent_budget_is_after_padding_and_only_row_active_gaps(kind, available):
    resolved = profile(container(kind, [slot(), slot("other", share=None, source="title")]))
    result = probe(resolved, {"table": measurement(), "other": measurement(30)})
    assert result["table"] == SourceInlineBudget("table", "/root/children/0",
                                                D(available), D(available) * D("0.4"))
    with pytest.raises(TypeError):
        result["table"] = result["table"]


def test_optional_absence_does_not_consume_row_gap_or_request_a_measurement():
    resolved = profile(container("row", [slot(), slot("other", share=None,
                                                     source="title", priority="optional")]))
    assert probe(resolved, {"table": measurement()})["table"].available_inline == 980


def test_grid_budget_uses_independent_spanned_cell_with_internal_gaps():
    resolved = profile(container("grid", [slot(cell={"column": 1, "row": 1, "columnSpan": 2})],
                                 columnTracks=[{"fixed": 200}, {"fixed": 300}, {"fr": 1}],
                                 rowTracks=[{"fr": 1}]))
    result = probe(resolved, {"table": measurement()})
    assert result["table"].available_inline == 520
    assert result["table"].ceiling == 208
    validate_source_inline_budgets(result, actual(resolved, {"table": measurement(100)}))


def test_flexible_grid_cell_is_not_recursively_shrunk_by_the_share():
    resolved = profile(container("grid", [slot(cell={"column": 1, "row": 1})],
                                 columnTracks=[{"fr": 1}, {"fr": 1}], rowTracks=[{"fr": 1}]))
    result = probe(resolved, {"table": measurement()})
    assert result["table"].available_inline == 480
    assert result["table"].ceiling == 192
    validate_source_inline_budgets(result, actual(resolved, {"table": measurement(100)}))


def test_intrinsic_grid_track_is_not_an_independent_budget():
    resolved = profile(container("grid", [slot(cell={"column": 1, "row": 1})],
                                 columnTracks=["content"], rowTracks=[{"fr": 1}]))
    with pytest.raises(LayoutError, match="E_LAYOUT_TABLE_OVERFLOW") as caught:
        probe(resolved, {"table": measurement()})
    assert caught.value.node_id == "table"


def test_content_parent_may_use_an_independent_sibling_floor_but_not_table_feedback():
    inner = container("column", [slot(), slot("other", share=None, source="title")],
                      id="inner", inlineSize="content", gap=0, padding=0)
    resolved = profile(container("column", [inner], gap=0, padding=0))
    source = {"table": measurement(), "other": measurement(100)}
    result = probe(resolved, source)
    assert result["table"].ceiling == 40
    validate_source_inline_budgets(result, actual(resolved, {**source, "table": measurement(40)}))
    with pytest.raises(LayoutError, match="E_LAYOUT_TABLE_OVERFLOW"):
        validate_source_inline_budgets(result, actual(resolved, {**source, "table": measurement(120)}))


def test_content_parent_without_other_inline_authority_is_rejected():
    inner = container("column", [slot()], id="inner", inlineSize="content", padding=0)
    resolved = profile(container("column", [inner]))
    with pytest.raises(LayoutError, match="E_LAYOUT_TABLE_OVERFLOW"):
        probe(resolved, {"table": measurement()})


def test_probe_does_not_mutate_resource_identity_inputs_or_existing_manifest():
    resolved = profile(container("row", [slot(), slot("other", share=None, source="title")]))
    sources = {"table": measurement(), "other": measurement(30)}
    original_profile, original_sources = deepcopy(resolved), deepcopy(sources)
    before = solve_layout(resolved, viewport_inline=1000, viewport_block=500, measurements=sources)
    probe(resolved, sources)
    after = solve_layout(resolved, viewport_inline=1000, viewport_block=500, measurements=sources)
    assert before.canonical_bytes() == after.canonical_bytes()
    assert resolved == original_profile
    assert sources == original_sources


def test_absent_declaration_has_no_probe_work_and_preserves_existing_solve():
    resolved = profile(container("row", [slot(share=None)]))
    assert probe(resolved, {}) == {}


@pytest.mark.parametrize("base", [(D(20), D(25), D(0)), (D(20), D(25), D(3))])
def test_fitting_track_base_is_exactly_preserved(base):
    budget = SourceInlineBudget("table", "/root/children/0", D(100), D(40))
    assert _limit_inline_base(base, budget) == base


def test_cap_is_flexible_maximum_not_a_fixed_share_or_an_extra_minimum():
    budget = SourceInlineBudget("table", "/root/children/0", D(100), D(40))
    capped = _limit_inline_base((D(20), None, D(1)), budget)
    assert capped == (D(20), D(40), D(1))
    assert _resolve_flexible_tracks([capped, (D(0), None, D(1))], D(100)) == [D(40), D(60)]
    assert _resolve_flexible_tracks([capped, (D(0), None, D(1))], D(50)) == [D(25), D(25)]


def test_mandatory_and_authored_minimum_is_not_erased_to_make_the_cap_fit():
    budget = SourceInlineBudget("table", "/root/children/0", D(100), D(40))
    with pytest.raises(LayoutError, match="E_LAYOUT_TABLE_OVERFLOW") as caught:
        _limit_inline_base((D(60), D(60), D(0)), budget)
    assert caught.value.path == budget.path
    assert caught.value.node_id == budget.slot_id


def test_closure_rejects_added_or_removed_active_table_budget():
    budget = SourceInlineBudget("table", "/root/children/0", D(100), D(40))
    with pytest.raises(LayoutError, match="E_LAYOUT_TABLE_OVERFLOW"):
        validate_source_inline_budgets({"table": budget}, {})
    with pytest.raises(LayoutError, match="E_LAYOUT_TABLE_OVERFLOW"):
        validate_source_inline_budgets({}, {"table": budget})


def bounded_measurement(inline, block=10):
    return Measurement(D(20), D(inline), D(inline), D(block), D(block), D(block))


def solve(resolved, sources, sizing):
    return solve_layout(resolved, viewport_inline=1000, viewport_block=500,
                        measurements=sources, sizing=sizing)


def bounds(manifest):
    return {item.node_id: item.bounds for item in manifest.decisions}


def test_row_capped_flexible_track_redistributes_space_to_plot():
    resolved = profile(container("row", [slot(share=0.2, inlineSize={"fr": 1}),
                                         slot("other", share=None, source="timeline", inlineSize={"fr": 1})]))
    budgets = probe(resolved, {"table": measurement(), "other": measurement(30)})
    sources = {"table": bounded_measurement(192), "other": measurement(30)}
    result = solve(resolved, sources, LayoutSizingContext(budgets))
    placed = bounds(result)
    assert placed["table"].inline_size == 192
    assert placed["other"].inline_size == 768
    assert not result.fit_warnings


@pytest.mark.parametrize("kind", ["column", "overlay", "flow"])
@pytest.mark.parametrize("size", ["content", {"fr": 1}, {"minmax": {"min": "content", "max": {"fr": 1}}}])
def test_cap_applies_to_cross_and_flow_allocation_without_stretch(kind, size):
    resolved = profile(container(kind, [slot(inlineSize=size)]))
    budgets = probe(resolved, {"table": measurement()})
    result = solve(resolved, {"table": bounded_measurement(392)}, LayoutSizingContext(budgets))
    assert bounds(result)["table"].inline_size == 392
    assert not result.fit_warnings


def test_flow_uses_bounded_width_before_selecting_lines():
    resolved = profile(container("flow", [slot(), slot("other", share=None, source="title")]))
    budgets = probe(resolved, {"table": measurement(), "other": measurement(550)})
    result = solve(resolved, {"table": bounded_measurement(392), "other": measurement(550)},
                   LayoutSizingContext(budgets))
    placed = bounds(result)
    assert placed["table"].block == placed["other"].block == 10
    assert placed["other"].inline == 422


def test_grid_keeps_full_independent_track_but_caps_its_table_slot():
    resolved = profile(container("grid", [slot(cell={"column": 1, "row": 1})],
                                 columnTracks=[{"fr": 1}, {"fr": 1}], rowTracks=["content"]))
    budgets = probe(resolved, {"table": measurement()})
    result = solve(resolved, {"table": bounded_measurement(192)}, LayoutSizingContext(budgets))
    assert budgets["table"].available_inline == 480
    assert bounds(result)["table"].inline_size == 192
    assert not result.fit_warnings


@pytest.mark.parametrize("kind", ["row", "column", "overlay", "flow", "grid"])
def test_actual_width_source_closure_is_shared_by_natural_and_arranged_block(kind):
    table = slot(inlineSize={"fr": 1})
    other = slot("other", share=None, source="title", inlineSize={"fr": 9})
    extra = {}
    if kind == "grid":
        table["cell"] = {"column": 1, "row": 1}
        other["cell"] = {"column": 2, "row": 1}
        extra = dict(columnTracks=[{"fr": 1}, {"fr": 9}], rowTracks=["content"])
    resolved = profile(container(kind, [table, other], **extra))
    raw_sources = {"table": measurement(), "other": measurement(30)}
    budgets = probe(resolved, raw_sources)
    widths = []

    def remeasure(slot_id, inline):
        assert slot_id == "table"
        widths.append(inline)
        lines = (D(1000) / inline).to_integral_value(rounding="ROUND_CEILING")
        return bounded_measurement(inline, lines * 10)

    sources = {**raw_sources, "table": bounded_measurement(budgets["table"].ceiling)}
    sizing = LayoutSizingContext(budgets, measure_source=remeasure)
    result = solve(resolved, sources, sizing)
    table_bounds = bounds(result)["table"]
    assert table_bounds.inline_size <= budgets["table"].ceiling
    expected = (D(1000) / table_bounds.inline_size).to_integral_value(rounding="ROUND_CEILING") * 10
    assert table_bounds.block_size >= expected
    natural = measure_natural_normal_flow_block(resolved, viewport_inline=1000,
                                                measurements=sources, sizing=sizing)
    assert natural >= expected + 20
    assert table_bounds.inline_size in widths
    assert not result.fit_warnings


@pytest.mark.parametrize("kind", ["row", "column", "overlay", "flow", "grid"])
def test_authored_fixed_inline_floor_above_cap_fails_in_every_container(kind):
    child = slot(inlineSize={"fixed": 500})
    extra = {}
    if kind == "grid":
        child["cell"] = {"column": 1, "row": 1}
        extra = dict(columnTracks=[{"fr": 1}], rowTracks=[{"fr": 1}])
    resolved = profile(container(kind, [child], **extra))
    budgets = probe(resolved, {"table": measurement()})
    with pytest.raises(LayoutError, match="E_LAYOUT_TABLE_OVERFLOW"):
        solve(resolved, {"table": bounded_measurement(392)}, LayoutSizingContext(budgets))


def test_empty_sizing_context_preserves_entire_existing_manifest():
    resolved = profile(container("row", [slot(share=None)]))
    sources = {"table": measurement(100)}
    assert solve(resolved, sources, None).canonical_bytes() == solve(
        resolved, sources, LayoutSizingContext({})).canonical_bytes()


def test_context_is_a_frozen_snapshot_not_a_mutable_resource_side_channel():
    budget = SourceInlineBudget("table", "/root/children/0", D(100), D(40))
    mutable = {"table": budget}
    sizing = LayoutSizingContext(mutable)
    mutable.clear()
    assert sizing.source_budgets == {"table": budget}
    with pytest.raises(TypeError):
        sizing.by_path[budget.path] = budget


def test_final_arrangement_rejects_table_dependent_parent_budget():
    inner = container("column", [slot(), slot("other", share=None, source="title")],
                      id="inner", inlineSize="content", gap=0, padding=0)
    resolved = profile(container("column", [inner], gap=0, padding=0))
    raw_sources = {"table": measurement(), "other": measurement(100)}
    budgets = probe(resolved, raw_sources)
    # Bad source closure still exposes uncapped intrinsic demand to the parent.
    with pytest.raises(LayoutError, match="E_LAYOUT_TABLE_OVERFLOW"):
        solve(resolved, raw_sources, LayoutSizingContext(budgets))


@pytest.mark.parametrize("content_sized", [False, True])
def test_content_extent_trials_keep_the_same_bounded_source_closure(content_sized):
    resolved = profile(container("column", [slot(inlineSize={"fr": 1}, blockSize="fill")]))
    budgets = probe(resolved, {"table": measurement()})
    widths = []

    def remeasure(slot_id, inline):
        widths.append(inline)
        return bounded_measurement(inline, 80)

    sizing = LayoutSizingContext(budgets, remeasure)
    sources = {"table": bounded_measurement(392)}
    extent = resolve_content_block_extent(resolved, viewport_inline=1000, minimum_block=50,
                                          measurements=sources, required_blocks={"table": D(80)},
                                          content_sized=content_sized, sizing=sizing)
    assert extent.extent == 100
    assert not extent.short_sources
    assert widths and set(widths) == {D(392)}
    final = solve_layout(resolved, viewport_inline=1000, viewport_block=extent.extent,
                         measurements=sources, content_sized=content_sized, sizing=sizing)
    assert bounds(final)["table"].block_size == 80
    assert not final.fit_warnings


@pytest.mark.parametrize("kind", ["row", "column", "overlay", "flow", "grid"])
def test_fitting_context_preserves_complete_manifest_and_baselines(kind):
    table = slot(share=1, inlineSize={"fr": 1})
    other = slot("other", share=None, source="title", inlineSize={"fr": 1})
    extra = {}
    if kind == "grid":
        table["cell"] = {"column": 1, "row": 1}
        other["cell"] = {"column": 2, "row": 1}
        extra = dict(columnTracks=[{"fr": 1}, {"fr": 1}], rowTracks=["content"])
    resolved = profile(container(kind, [table, other], **extra))
    source = Measurement(D(20), D(20), D(20), D(10), D(10), D(10), D(7), D(7))
    sources = {"table": source, "other": source}
    sizing = LayoutSizingContext(probe(resolved, sources), lambda slot_id, inline: source)
    assert solve(resolved, sources, sizing).canonical_bytes() == solve(resolved, sources, None).canonical_bytes()


def test_source_mandatory_width_must_fit_actual_fr_allocation_not_just_ceiling():
    resolved = profile(container("row", [slot(inlineSize={"fr": 1}),
                                         slot("other", share=None, source="title", inlineSize={"fr": 99})]))
    raw_sources = {"table": measurement(), "other": measurement(30)}
    budgets = probe(resolved, raw_sources)
    sizing = LayoutSizingContext(budgets, lambda slot_id, inline: bounded_measurement(inline))
    with pytest.raises(LayoutError, match="E_LAYOUT_TABLE_OVERFLOW"):
        solve(resolved, {**raw_sources, "table": bounded_measurement(384)}, sizing)


def test_flow_item_minimum_above_ceiling_is_not_silently_reduced():
    resolved = profile(container("flow", [slot(share=0.01)]))
    budgets = probe(resolved, {"table": measurement()})
    with pytest.raises(LayoutError, match="E_LAYOUT_TABLE_OVERFLOW"):
        solve(resolved, {"table": Measurement(D(1), D(9), D(9), D(10), D(10), D(10))},
               LayoutSizingContext(budgets))


@pytest.mark.parametrize("kind", ["row", "column", "overlay", "flow", "grid"])
def test_authored_aspect_size_above_cap_is_not_clamped(kind):
    child = slot(inlineSize={"aspectRatio": 2}, blockSize={"fixed": 500})
    extra = {}
    if kind == "grid":
        child["cell"] = {"column": 1, "row": 1}
        extra = dict(columnTracks=[{"fr": 1}], rowTracks=[{"fixed": 500}])
    resolved = profile(container(kind, [child], **extra))
    budgets = probe(resolved, {"table": measurement()})
    with pytest.raises(LayoutError, match="E_LAYOUT_TABLE_OVERFLOW"):
        solve(resolved, {"table": bounded_measurement(392)}, LayoutSizingContext(budgets))


@pytest.mark.parametrize("content_sized", [False, True])
def test_coupled_extent_builds_independent_budgets_for_each_candidate(content_sized):
    inner = container("row", [slot(blockSize="fill"),
                              slot("other", share=None, source="timeline", inlineSize="fill", blockSize="fill")],
                      id="inner", inlineSize={"aspectRatio": 2}, blockSize="fill", padding=0, gap=0)
    resolved = profile(container("column", [inner], padding=0, gap=0))
    raw_sources = {"table": measurement(), "other": measurement(30)}
    requested_budgets = []

    def for_extent(block):
        budgets = resolve_source_inline_budgets(resolved, viewport_inline=1000, viewport_block=block,
                                               measurements=raw_sources, content_sized=content_sized)
        assert budgets["table"].ceiling == block * D("0.8")
        requested_budgets.append((block, budgets["table"].ceiling))
        return LayoutSizingContext(budgets, lambda slot_id, inline: bounded_measurement(inline, 80))

    extent = resolve_content_block_extent(resolved, viewport_inline=1000, minimum_block=50,
                                          measurements=raw_sources, required_blocks={"table": D(80)},
                                          content_sized=content_sized, sizing=for_extent)
    assert extent.extent == 80
    assert not extent.short_sources
    assert len(set(ceiling for _, ceiling in requested_budgets)) > 1
    final = solve_layout(resolved, viewport_inline=1000, viewport_block=extent.extent,
                         measurements=raw_sources, content_sized=content_sized, sizing=for_extent(D(80)))
    assert bounds(final)["table"].inline_size == 64
    assert bounds(final)["table"].block_size == 80
    assert not final.fit_warnings
