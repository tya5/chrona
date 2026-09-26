"""Unit tests for the flexible-track allocation algorithm (#487, ADR-0032).

`_resolve_flexible_tracks` is the pure (minimum, maximum, weight) -> sizes step
`_allocate` delegates to after resolving each spec through `_spec_base`. It is
tested directly here because the public Layout Profile grammar cannot express a
flexible track with a finite `maximum`: `_spec_base`'s `minmax` branch takes a
track's weight from its `max` sub-spec, and every sub-spec that yields a
nonzero weight (`fill`, `{fr: n}`) also yields an unbounded (`None`) maximum.
The maximum-clamp path is still exercised directly, as forward-compatible,
CSS-Grid-correct behavior for any future spec that combines the two.
"""
from decimal import Decimal

import pytest
import yaml

from chrona.presentation.layout.engine import _resolve_flexible_tracks, solve_layout
from chrona.presentation.layout.model import Measurement
from chrona.presentation.layout.profile import resolve_layout_profile


ZERO = Decimal(0)


def base(minimum: int, maximum: int | None, weight: int) -> tuple[Decimal, Decimal | None, Decimal]:
    return Decimal(minimum), (Decimal(maximum) if maximum is not None else None), Decimal(weight)


def test_minimum_exceeding_its_share_is_frozen_and_the_rest_redistributes_without_oversubscribing():
    """A track whose `minmax` minimum exceeds its even fr share takes exactly
    that minimum, and the remaining flexible track absorbs the rest of the
    available space -- the total never exceeds `available`."""
    bases = [base(80, None, 1), base(0, None, 1)]
    sizes = _resolve_flexible_tracks(bases, Decimal(100))
    assert sizes == [Decimal(80), Decimal(20)]
    assert sum(sizes, ZERO) == Decimal(100)


def test_maximum_smaller_than_its_share_is_clamped_and_the_rest_redistributes():
    """A track whose `maximum` is smaller than its even fr share is frozen at
    that maximum, and the remaining flexible track absorbs the redistributed
    surplus -- the total still lands exactly at `available`."""
    bases = [base(0, 20, 1), base(0, None, 1)]
    sizes = _resolve_flexible_tracks(bases, Decimal(100))
    assert sizes == [Decimal(20), Decimal(80)]
    assert sum(sizes, ZERO) == Decimal(100)


def test_all_zero_minima_split_available_space_exactly_by_weight():
    """With every flexible track's minimum at 0, `max(minimum, share) ==
    share` for each track: this is numerically identical to the pre-#487
    additive rule (`minimum + share == 0 + share == share`), so no existing
    zero-minimum profile (a plain `fill` or `{fr: n}` track) changes."""
    bases = [base(0, None, 1), base(0, None, 3)]
    sizes = _resolve_flexible_tracks(bases, Decimal(100))
    assert sizes == [Decimal(25), Decimal(75)]
    assert sum(sizes, ZERO) == Decimal(100)


def test_minima_exceeding_available_space_keep_every_track_at_its_minimum():
    """When the flexible tracks' minima alone already exceed `available`,
    every flexible track takes its minimum; the caller's existing typed
    fit-shortage/overflow completion covers the resulting oversubscription, as
    it already does for any other under-sized valid profile."""
    bases = [base(60, None, 1), base(60, None, 1)]
    sizes = _resolve_flexible_tracks(bases, Decimal(100))
    assert sizes == [Decimal(60), Decimal(60)]
    assert sum(sizes, ZERO) == Decimal(120) > Decimal(100)


def _minmax_profile(min_a: int, min_b: int):
    raw = {
        "version": "chrona/layout-profile/v0.9", "id": "flex", "flowDirection": "horizontal",
        "dependencyNetworkFlowDirection": "horizontal", "requiredThemeTokens": ["spacing.none"],
        "reviewSurface": {"rowDistribution": "pack",
                          "backgroundExtents": {"rowBand": "table", "groupBand": "timeline",
                                                 "groupHeaderBand": "both", "calendarClosed": "timeline"},
                          "annotationRouting": {"maxBends": 4, "maxDetourRatio": 2}},
        "root": {"id": "root", "kind": "row", "inlineSize": "fill", "blockSize": "fill",
                 "gap": {"token": "spacing.none"}, "padding": {"token": "spacing.none"},
                 "alignItems": "stretch", "justifyContent": "start", "children": [
                     {"id": "legend", "kind": "slot", "source": "legend",
                      "inlineSize": {"minmax": {"min": {"fixed": min_a}, "max": {"fr": 1}}},
                      "blockSize": "fill", "place": {"inline": "stretch", "block": "stretch", "safety": "strict"},
                      "priority": "required", "overflow": "visible-overflow"},
                     {"id": "notes", "kind": "slot", "source": "notes",
                      "inlineSize": {"minmax": {"min": {"fixed": min_b}, "max": {"fr": 1}}},
                      "blockSize": "fill", "place": {"inline": "stretch", "block": "stretch", "safety": "strict"},
                      "priority": "required", "overflow": "visible-overflow"},
                 ]},
    }
    theme = {"body": {"values": {"spacing.none": {"type": "number", "value": 0}}}}
    return resolve_layout_profile(raw, available_sources={"legend", "notes"}, theme=theme)


def test_end_to_end_minmax_minimum_never_oversubscribes_the_row_through_solve_layout():
    """The same min-exceeds-share redistribution, reached through the public
    Layout Profile grammar (`minmax: {min: {fixed: …}, max: {fr: 1}}`) and
    `solve_layout`, not only the internal pure function."""
    measurements = {"legend": Measurement(*(Decimal(0),) * 6), "notes": Measurement(*(Decimal(0),) * 6)}
    resolved = _minmax_profile(min_a=800, min_b=0)
    manifest = solve_layout(resolved, viewport_inline=1000, viewport_block=100, measurements=measurements)
    bounds = {item.node_id: item.bounds for item in manifest.decisions}
    assert bounds["legend"].inline_size == Decimal(800)
    assert bounds["notes"].inline_size == Decimal(200)
    assert bounds["legend"].inline_size + bounds["notes"].inline_size == Decimal(1000)
    assert not manifest.fit_warnings
