"""Padding-only calendar buckets disappear before axis fitting (#1855)."""
from dataclasses import replace
from datetime import date, datetime

import pytest

from chrona.presentation.layout.model import LayoutError
from chrona.presentation.layout.surface_axis import measure_axis_tier, measure_surface_axis
from chrona.presentation.layout.surface_base import prepare_surface_base
from chrona.presentation.model.projection import WindowMode
from chrona.presentation.model.surface_content import AxisLabelIntent, AxisTier
from tests.unit.chrona.presentation.layout.test_surface_axis_tier_geometry import _axis_request


def _request(*, envelope=(date(2026, 10, 5), date(2027, 5, 13)), every=1):
    tier = AxisTier("quarter", every, "labels", AxisLabelIntent(
        "year-quarter", (), "center", "thin-with-record", "horizontal", "ja-JP"))
    request = _axis_request((tier,))
    return replace(request, projection=replace(
        request.projection,
        window=(date(2026, 9, 13), date(2027, 6, 4)),
        unpadded_window=envelope,
    ))


def test_padding_only_quarter_has_no_outcome_and_retained_quarter_keeps_natural_identity():
    request = _request()
    scale = prepare_surface_base(request).scale

    measured = measure_axis_tier(request, scale, 0, request.surface_content.axis_tiers[0])

    assert [(item.start, item.end, item.natural_start, item.natural_end)
            for item in measured.outcomes] == [
        (date(2026, 10, 1), date(2027, 1, 1), date(2026, 10, 1), date(2027, 1, 1)),
        (date(2027, 1, 1), date(2027, 4, 1), date(2027, 1, 1), date(2027, 4, 1)),
        (date(2027, 4, 1), date(2027, 6, 4), date(2027, 4, 1), date(2027, 7, 1)),
    ]
    assert [item.candidate_id for item in measured.outcomes] == [
        "axis-label:0:1", "axis-label:0:2", "axis-label:0:3",
    ]
    assert not any("axis-label:0:0" in diagnostic for diagnostic in measured.diagnostics)


def test_padding_only_filter_applies_to_band_label_and_both_grid_tier_intervals():
    tiers = (
        AxisTier("quarter", 1, "band"),
        AxisTier("quarter", 1, "grid-major"),
        AxisTier("quarter", 1, "labels", AxisLabelIntent(
            "year-quarter", (), "center", "thin-with-record", "horizontal", "ja-JP")),
        AxisTier("month", 1, "grid-minor"),
    )
    request = _axis_request(tiers)
    request = replace(request, projection=replace(
        request.projection,
        window=(date(2026, 9, 13), date(2027, 6, 4)),
        unpadded_window=(date(2026, 10, 5), date(2027, 5, 13)),
    ))
    scale = prepare_surface_base(request).scale

    measured = measure_surface_axis(request, scale)

    assert all(item.natural_start != date(2026, 7, 1)
               for tier in measured.tiers for item in tier.intervals)
    assert [item.natural_start for item in measured.tiers[0].intervals] == [
        date(2026, 10, 1), date(2027, 1, 1), date(2027, 4, 1),
    ]
    assert [item.natural_start for item in measured.tiers[3].intervals] == [
        date(2026, 10, 1), date(2026, 11, 1), date(2026, 12, 1),
        date(2027, 1, 1), date(2027, 2, 1), date(2027, 3, 1), date(2027, 4, 1),
        date(2027, 5, 1),
    ]


def test_authored_every_is_applied_before_padding_only_filtering():
    request = _request(every=2)
    scale = prepare_surface_base(request).scale

    measured = measure_axis_tier(request, scale, 0, request.surface_content.axis_tiers[0])

    assert [(item.index, item.natural_start) for item in measured.intervals] == [
        (2, date(2027, 1, 1)),
    ]


def test_point_envelope_keeps_its_containing_quarter_only():
    request = _request(envelope=(date(2026, 10, 5), date(2026, 10, 6)))
    scale = prepare_surface_base(request).scale

    measured = measure_axis_tier(request, scale, 0, request.surface_content.axis_tiers[0])

    assert [(item.natural_start, item.natural_end) for item in measured.intervals] == [
        (date(2026, 10, 1), date(2027, 1, 1)),
    ]


def test_interior_empty_calendar_month_remains_inside_the_unpadded_envelope():
    tier = AxisTier("month", 1, "grid-minor")
    request = _axis_request((tier,))
    request = replace(request, projection=replace(
        request.projection,
        window=(date(2026, 9, 13), date(2027, 1, 7)),
        unpadded_window=(date(2026, 10, 5), date(2026, 12, 16)),
    ))
    scale = prepare_surface_base(request).scale

    measured = measure_axis_tier(request, scale, 0, tier)

    assert [item.natural_start for item in measured.intervals] == [
        date(2026, 10, 1), date(2026, 11, 1), date(2026, 12, 1),
    ]


def test_missing_envelope_does_not_infer_padding_or_drop_calendar_buckets():
    request = _request(envelope=None)
    request = replace(request, projection=replace(
        request.projection, window_mode=WindowMode.EXPLICIT))
    scale = prepare_surface_base(request).scale

    measured = measure_axis_tier(request, scale, 0, request.surface_content.axis_tiers[0])

    assert measured.intervals[0].natural_start == date(2026, 7, 1)
    assert measured.outcomes[0].candidate_id == "axis-label:0:0"


def test_automatic_tier_without_envelope_keeps_padding_only_candidate():
    tier = AxisTier("auto", 1, "labels", AxisLabelIntent(
        None, (("quarter", "year-quarter"),), "center", "thin-with-record", "horizontal", "ja-JP"))
    request = _axis_request((tier,))
    request = replace(request, projection=replace(
        request.projection,
        window=(date(2026, 9, 13), date(2027, 6, 4)),
        unpadded_window=None,
    ))
    scale = prepare_surface_base(request).scale

    measured = measure_axis_tier(request, scale, 0, tier)

    assert measured.intervals[0].natural_start == date(2026, 7, 1)
    assert measured.outcomes[0].candidate_id == "axis-label:0:0"


@pytest.mark.parametrize("envelope", [
    (date(2026, 9, 12), date(2027, 5, 13)),
    (date(2026, 10, 5), date(2026, 10, 5)),
    (None, date(2027, 5, 13)),
    (datetime(2026, 10, 5), date(2027, 5, 13)),
])
@pytest.mark.parametrize("mode", [WindowMode.SELECTED_PLANNED, WindowMode.EXPLICIT])
def test_malformed_unpadded_envelope_fails_layout_validation(envelope, mode):
    request = _request(envelope=envelope)
    request = replace(request, projection=replace(request.projection, window_mode=mode))
    scale = prepare_surface_base(request).scale

    with pytest.raises(LayoutError, match="E_PRESENTATION_PROJECTION_REQUIRED") as error:
        measure_axis_tier(request, scale, 0, request.surface_content.axis_tiers[0])
    assert error.value.path == "/projection/unpaddedWindow"
    assert "positive Date interval enclosed by projection.window" in error.value.detail


def test_explicit_window_with_otherwise_valid_envelope_is_rejected():
    request = _request()
    request = replace(request, projection=replace(
        request.projection, window_mode=WindowMode.EXPLICIT))
    scale = prepare_surface_base(request).scale

    with pytest.raises(LayoutError) as error:
        measure_axis_tier(request, scale, 0, request.surface_content.axis_tiers[0])

    assert error.value.path == "/projection/unpaddedWindow"
