from datetime import date

import pytest

from chrona.presentation.layout.mark_aware_scale import PointMarkFootprint, inset_scale_for_point_facets
from chrona.presentation.layout.model import LayoutError
from chrona.presentation.layout.surface_quality import ScalePlacement


def _scale() -> ScalePlacement:
    return ScalePlacement("table-timeline", "primary", date(2026, 1, 1), date(2026, 1, 11),
                          0.0, 100.0, 0.0, 10.0)


def test_first_and_last_point_facets_reserve_their_resolved_protrusions() -> None:
    scale = inset_scale_for_point_facets(
        _scale(),
        (
            PointMarkFootprint(date(2026, 1, 1), -4.0, 3.0),
            PointMarkFootprint(date(2026, 1, 11), 97.0, 105.0),
        ),
    )

    assert (scale.domain_start, scale.domain_end) == (date(2026, 1, 1), date(2026, 1, 11))
    assert (scale.range_start, scale.range_end) == (4.0, 95.0)
    assert scale.origin == scale.range_start
    assert scale.origin + (scale.domain_end - scale.domain_start).days * scale.unit_ratio == 95.0


def test_no_point_facets_preserves_the_full_scale_object() -> None:
    full = _scale()

    assert inset_scale_for_point_facets(full, ()) is full


def test_nonpositive_inner_range_is_a_layout_mark_overflow() -> None:
    with pytest.raises(LayoutError, match="E_LAYOUT_MARK_OVERFLOW"):
        inset_scale_for_point_facets(
            _scale(),
            (PointMarkFootprint(date(2026, 1, 1), -60.0, 3.0),
             PointMarkFootprint(date(2026, 1, 11), 97.0, 160.0)),
        )
