"""#1906: finite minmax intervals participate as bounded unit-weight tracks."""
from dataclasses import replace
from decimal import Decimal

import pytest

from chrona.presentation.layout.engine import (
    LayoutSizingContext,
    SourceInlineBudget,
    _spec_base,
    solve_layout,
)
from chrona.presentation.layout.model import CountDependentHeadingFitError, LayoutError
from tests.unit.chrona.presentation.layout.test_cross_size_stretch import (
    container, decisions, measurement, resolved, slot,
)


def _pair(axis, bounded_spec, extent):
    bounded = slot("bounded", inline=bounded_spec if axis == "row" else "fill",
                   block=bounded_spec if axis == "column" else "fill")
    flexible = slot("flexible")
    root = container(axis, [bounded, flexible])
    profile = resolved(root, {"bounded": measurement(), "flexible": measurement()})
    manifest = solve_layout(profile,
                            viewport_inline=extent if axis == "row" else 200,
                            viewport_block=extent if axis == "column" else 200,
                            measurements={"bounded": measurement(), "flexible": measurement()})
    bounds = decisions(manifest)
    return (bounds["bounded"].inline_size, bounds["flexible"].inline_size) if axis == "row" else (
        bounds["bounded"].block_size, bounds["flexible"].block_size)


@pytest.mark.parametrize("axis", ["row", "column"])
@pytest.mark.parametrize(("extent", "expected"), [
    (40, (20, 20)),
    (100, (50, 50)),
    (220, (80, 140)),
])
def test_finite_minmax_shrinks_and_grows_as_a_bounded_unit_track(axis, extent, expected):
    spec = {"minmax": {"min": {"fixed": 20}, "max": {"fixed": 80}}}

    sizes = _pair(axis, spec, extent)

    assert sizes == tuple(Decimal(value) for value in expected)


@pytest.mark.parametrize("axis", ["row", "column"])
def test_fixed_point_and_explicit_fr_maximum_keep_their_existing_meaning(axis):
    fixed = {"fixed": 40}
    point = {"minmax": {"min": {"fixed": 40}, "max": {"fixed": 40}}}
    weighted = {"minmax": {"min": {"fixed": 20}, "max": {"fr": 2}}}

    assert _pair(axis, fixed, 100) == (Decimal(40), Decimal(60))
    assert _pair(axis, point, 100) == (Decimal(40), Decimal(60))
    first, second = _pair(axis, weighted, 100)
    assert float(first) == pytest.approx(200 / 3)
    assert float(second) == pytest.approx(100 / 3)


def test_grid_column_track_uses_the_same_bounded_interval_allocation():
    spec = {"minmax": {"min": {"fixed": 20}, "max": {"fixed": 80}}}
    bounded, flexible = slot("bounded"), slot("flexible")
    bounded["cell"], flexible["cell"] = {"column": 1, "row": 1}, {"column": 2, "row": 1}
    root = container("grid", [bounded, flexible], columnTracks=[spec, "fill"], rowTracks=["fill"])
    measures = {"bounded": measurement(), "flexible": measurement()}
    profile = resolved(root, measures)

    manifest = solve_layout(profile, viewport_inline=100, viewport_block=100, measurements=measures)
    bounds = decisions(manifest)

    assert (bounds["bounded"].inline_size, bounds["flexible"].inline_size) == (
        Decimal(50), Decimal(50))


def test_authored_fixed_minimum_above_finite_maximum_is_rejected():
    spec = {"minmax": {"min": {"fixed": 90}, "max": {"fixed": 80}}}
    bounded, flexible = slot("bounded"), slot("flexible")
    bounded["inlineSize"] = spec
    root = container("row", [bounded, flexible])
    measures = {"bounded": measurement(), "flexible": measurement()}
    profile = resolved(root, measures)

    with pytest.raises(LayoutError, match="E_LAYOUT_CONSTRAINT_CONTRADICTORY"):
        solve_layout(profile, viewport_inline=100, viewport_block=100, measurements=measures)


@pytest.mark.parametrize("budget_ceiling", [70, 100])
def test_budgeted_intrinsic_minimum_is_not_erased_by_finite_track_cap(budget_ceiling):
    bounded = slot("bounded", inline={"minmax": {"min": "content", "max": {"fixed": 80}}})
    root = container("row", [bounded])
    measured = measurement(min_inline=90, preferred_inline=100)
    profile = resolved(root, {"bounded": measured})
    sizing = LayoutSizingContext({"bounded": SourceInlineBudget(
        "bounded", "/root/children/0", Decimal(100), Decimal(budget_ceiling))})

    with pytest.raises(LayoutError) as caught:
        _spec_base(bounded["inlineSize"], axis="inline", measurement=measured,
                   profile=profile, path="/root/children/0/inlineSize", sizing=sizing)

    assert caught.value.diagnostic_id == "E_LAYOUT_TABLE_OVERFLOW"
    assert caught.value.path == "/root/children/0"
    assert caught.value.node_id == "bounded"


def test_budgeted_count_dependent_minimum_above_track_cap_keeps_heading_error():
    bounded = slot("bounded", inline={"minmax": {"min": "content", "max": {"fixed": 80}}})
    root = container("row", [bounded])
    measured = replace(measurement(min_inline=90, preferred_inline=100),
                       figure_dependencies=frozenset({"notes"}))
    profile = resolved(root, {"bounded": measured})
    sizing = LayoutSizingContext({"bounded": SourceInlineBudget(
        "bounded", "/root/children/0", Decimal(100), Decimal(100), "heading")})

    with pytest.raises(CountDependentHeadingFitError) as caught:
        _spec_base(bounded["inlineSize"], axis="inline", measurement=measured,
                   profile=profile, path="/root/children/0/inlineSize", sizing=sizing)

    assert caught.value.figure_ids == {"notes"}
