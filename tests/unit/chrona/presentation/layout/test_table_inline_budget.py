"""Independent-budget and track-base components, not surface acceptance."""
from copy import deepcopy
from decimal import Decimal as D

import pytest

from chrona.presentation.layout.engine import (
    TableInlineBudget, _Arranger, _limit_inline_base, _resolve_flexible_tracks,
    resolve_table_inline_budgets, solve_layout, validate_table_inline_budgets,
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
    return resolve_table_inline_budgets(resolved, viewport_inline=1000,
                                       viewport_block=500, measurements=measurements)


def actual(resolved, measurements):
    arranger = _Arranger(resolved, measurements, collect_table_budgets=True)
    arranger._record_inline_budget(resolved.profile["root"], "/root", D(1000))
    arranger.arrange(resolved.profile["root"], "/root", Rect(D(0), D(0), D(1000), D(500)))
    return arranger.table_inline_budgets


@pytest.mark.parametrize("kind,available", [("row", 960), ("column", 980),
                                          ("overlay", 980), ("flow", 980)])
def test_parent_budget_is_after_padding_and_only_row_active_gaps(kind, available):
    resolved = profile(container(kind, [slot(), slot("other", share=None, source="title")]))
    result = probe(resolved, {"table": measurement(), "other": measurement(30)})
    assert result["table"] == TableInlineBudget("table", "/root/children/0",
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
    validate_table_inline_budgets(result, actual(resolved, {"table": measurement(100)}))


def test_flexible_grid_cell_is_not_recursively_shrunk_by_the_share():
    resolved = profile(container("grid", [slot(cell={"column": 1, "row": 1})],
                                 columnTracks=[{"fr": 1}, {"fr": 1}], rowTracks=[{"fr": 1}]))
    result = probe(resolved, {"table": measurement()})
    assert result["table"].available_inline == 480
    assert result["table"].ceiling == 192
    validate_table_inline_budgets(result, actual(resolved, {"table": measurement(100)}))


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
    validate_table_inline_budgets(result, actual(resolved, {**source, "table": measurement(40)}))
    with pytest.raises(LayoutError, match="E_LAYOUT_TABLE_OVERFLOW"):
        validate_table_inline_budgets(result, actual(resolved, {**source, "table": measurement(120)}))


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
    budget = TableInlineBudget("table", "/root/children/0", D(100), D(40))
    assert _limit_inline_base(base, budget) == base


def test_cap_is_flexible_maximum_not_a_fixed_share_or_an_extra_minimum():
    budget = TableInlineBudget("table", "/root/children/0", D(100), D(40))
    capped = _limit_inline_base((D(20), None, D(1)), budget)
    assert capped == (D(20), D(40), D(1))
    assert _resolve_flexible_tracks([capped, (D(0), None, D(1))], D(100)) == [D(40), D(60)]
    assert _resolve_flexible_tracks([capped, (D(0), None, D(1))], D(50)) == [D(25), D(25)]


def test_mandatory_and_authored_minimum_is_not_erased_to_make_the_cap_fit():
    budget = TableInlineBudget("table", "/root/children/0", D(100), D(40))
    with pytest.raises(LayoutError, match="E_LAYOUT_TABLE_OVERFLOW") as caught:
        _limit_inline_base((D(60), D(60), D(0)), budget)
    assert caught.value.path == budget.path
    assert caught.value.node_id == budget.slot_id


def test_closure_rejects_added_or_removed_active_table_budget():
    budget = TableInlineBudget("table", "/root/children/0", D(100), D(40))
    with pytest.raises(LayoutError, match="E_LAYOUT_TABLE_OVERFLOW"):
        validate_table_inline_budgets({"table": budget}, {})
    with pytest.raises(LayoutError, match="E_LAYOUT_TABLE_OVERFLOW"):
        validate_table_inline_budgets({}, {"table": budget})
