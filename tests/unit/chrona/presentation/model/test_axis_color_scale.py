from datetime import date
import pytest

from chrona.presentation.model.axis_color_scale import (
    AxisBandFillSpec,
    AxisBandScaleError,
    resolve_axis_band_scales,
)
from chrona.presentation.model.surface_content import AxisTier


def _tier(unit, *, every=1, role="band", fill=None):
    return AxisTier(unit=unit, every=every, role=role, fill_scale=fill)


def _slots(values, colors=None):
    colors = colors or ("#112233", "#DDAA44", "#227744", "#553399", "#AA3355")
    return {value: f"c{index}" for index, value in enumerate(values)}, {
        f"c{index}": colors[index % len(colors)] for index, value in enumerate(values)
    }


def _run(tiers, *, start="2026-01-01", end="2026-06-01", scales=None, categories=None, fiscal=1):
    return resolve_axis_band_scales(
        tiers,
        window=(date.fromisoformat(start), date.fromisoformat(end)),
        fiscal_start_month=fiscal,
        scales=scales or {}, categories=categories or {},
    )


def test_no_opt_in_is_a_true_noop_without_calendar_or_theme_validation():
    result = resolve_axis_band_scales(
        (_tier("auto", role="labels"),), window=(date(2026, 2, 1), date(2026, 1, 1)),
        fiscal_start_month=99, scales=None, categories=None,
    )
    assert result.paints == ()
    assert result.collisions == ()


def test_alternating_uses_the_two_explicit_parity_values_and_retained_ordinals():
    slots, categories = _slots(("0", "1"))
    result = _run(
        (_tier("month", every=2, fill=AxisBandFillSpec("alt", "alternating")),),
        scales={"alt": {"slots": slots}}, categories=categories,
    )
    assert tuple(color for _, color in result.paints) == ("#112233", "#112233", "#112233")
    assert len({placement for placement, _ in result.paints}) == 3


def test_interval_key_requires_exact_slots_for_whole_selected_domain():
    slots, categories = _slots(("0", "1", "2", "3", "4"))
    result = _run(
        (_tier("month", fill=AxisBandFillSpec("months", "interval")),),
        scales={"months": {"slots": slots}}, categories=categories,
    )
    assert tuple(color for _, color in result.paints) == tuple(categories[slots[str(i)]] for i in range(5))


def test_parent_tier_can_appear_later_and_months_use_unique_quarter_containers():
    slots, categories = _slots(("0", "1"))
    result = _run(
        (
            _tier("month", fill=AxisBandFillSpec("quarter-colors", "interval", containing_tier=1)),
            _tier("quarter"),
        ),
        scales={"quarter-colors": {"slots": slots}}, categories=categories,
    )
    assert tuple(color for _, color in result.paints) == (
        "#112233", "#112233", "#112233", "#DDAA44", "#DDAA44",
    )


def test_fiscal_quarter_parent_uses_natural_interval_identity_when_window_is_clipped():
    slots, categories = _slots(("0", "1"))
    result = _run(
        (
            _tier("month", fill=AxisBandFillSpec("fiscal", "interval", containing_tier=1)),
            _tier("quarter"),
        ),
        start="2026-08-15", end="2026-11-01", fiscal=7,
        scales={"fiscal": {"slots": slots}}, categories=categories,
    )
    assert len(result.paints) == 3
    assert result.paints[0][1] == result.paints[1][1]
    assert result.paints[2][1] != result.paints[0][1]


def test_fiscal_year_parent_contains_quarters_across_a_clipped_window():
    slots, categories = _slots(("0", "1", "2"))
    result = _run(
        (
            _tier("quarter", fill=AxisBandFillSpec("fiscal-years", "interval", containing_tier=1)),
            _tier("year"),
        ),
        start="2026-03-15", end="2027-08-15", fiscal=7,
        scales={"fiscal-years": {"slots": slots}}, categories=categories,
    )
    colors = tuple(color for _, color in result.paints)
    assert len(colors) == 7
    assert colors[:2] == ("#112233", "#112233")
    assert colors[2:6] == ("#DDAA44", "#DDAA44", "#DDAA44", "#DDAA44")
    assert colors[6] == "#227744"


def test_parent_every_gap_rejects_instead_of_using_nearest_parent():
    slots, categories = _slots(("0", "2"))
    with pytest.raises(AxisBandScaleError, match="E_PRESENTATION_AXIS_SCALE_PARENT"):
        _run(
            (_tier("month", fill=AxisBandFillSpec("s", "interval", containing_tier=1)),
             _tier("quarter", every=2)),
            start="2026-01-01", end="2026-10-01",
            scales={"s": {"slots": slots}}, categories=categories,
        )


def test_week_crossing_month_boundary_has_no_synthetic_container():
    slots, categories = _slots(("0",))
    with pytest.raises(AxisBandScaleError, match="E_PRESENTATION_AXIS_SCALE_PARENT"):
        _run(
            (_tier("week", fill=AxisBandFillSpec("s", "interval", containing_tier=1)),
             _tier("month")),
            start="2026-03-01", end="2026-04-01",
            scales={"s": {"slots": slots}}, categories=categories,
        )


@pytest.mark.parametrize("parent, parent_unit, parent_role", [
    (0, "quarter", "band"), (1, "month", "band"), (1, "day", "band"), (1, "quarter", "labels"),
])
def test_self_same_finer_and_nonband_parent_targets_are_rejected(parent, parent_unit, parent_role):
    tiers = (_tier("quarter", fill=AxisBandFillSpec("s", "interval", parent)),
             _tier(parent_unit, role=parent_role))
    with pytest.raises(AxisBandScaleError, match="E_PRESENTATION_AXIS_SCALE_PARENT"):
        _run(tiers, scales={"s": {"slots": {"0": "c"}}}, categories={"c": "#112233"})


def test_auto_and_non_band_target_rejected():
    with pytest.raises(AxisBandScaleError, match="E_PRESENTATION_AXIS_SCALE_TARGET"):
        _run((_tier("auto", fill=AxisBandFillSpec("s", "interval")),))
    with pytest.raises(AxisBandScaleError, match="E_PRESENTATION_AXIS_SCALE_TARGET"):
        _run((_tier("month", role="labels", fill=AxisBandFillSpec("s", "interval")),))


@pytest.mark.parametrize("mapping", [
    {"slots": {"0": "c0", "1": "c1", "2": "c2", "3": "c3"}},
    {"slots": {"0": "c0", "1": "c1", "2": "c2", "3": "c3", "4": "c4", "extra": "c5"}},
    {"palette": ["c0", "c1"]},
])
def test_missing_extra_and_palette_mappings_are_rejected(mapping):
    with pytest.raises(AxisBandScaleError, match="E_PRESENTATION_SCALE_MAPPING"):
        _run((_tier("month", fill=AxisBandFillSpec("s", "interval")),),
             scales={"s": mapping}, categories={f"c{i}": "#112233" for i in range(6)})


def test_unknown_scheme_slot_and_invalid_color_are_rejected():
    for slots, categories in (({"0": "missing", "1": "c1", "2": "c2", "3": "c3", "4": "c4"}, {f"c{i}": "#112233" for i in range(5)}),
                              ({str(i): f"c{i}" for i in range(5)}, {**{f"c{i}": "#112233" for i in range(5)}, "c2": "red"})):
        with pytest.raises(AxisBandScaleError, match="E_PRESENTATION_SCALE_MAPPING"):
            _run((_tier("month", fill=AxisBandFillSpec("s", "interval")),),
                 scales={"s": {"slots": slots}}, categories=categories)


def test_separability_checks_domain_values_not_repeated_interval_cells():
    slots = {str(i): "same" for i in range(5)}
    result = _run((_tier("month", fill=AxisBandFillSpec("s", "interval")),),
                  scales={"s": {"slots": slots}}, categories={"same": "#112233"})
    assert len(result.paints) == 5
    assert tuple((item.first, item.second) for item in result.collisions) == tuple(
        (str(i), str(j)) for i in range(5) for j in range(i + 1, 5)
    )


def test_alternating_separability_is_checked_on_two_domain_classes_once():
    slots = {"0": "same", "1": "same"}
    result = _run((_tier("month", fill=AxisBandFillSpec("s", "alternating")),),
                  scales={"s": {"slots": slots}}, categories={"same": "#112233"})
    assert len(result.collisions) == 1
    assert (result.collisions[0].first, result.collisions[0].second) == ("0", "1")
