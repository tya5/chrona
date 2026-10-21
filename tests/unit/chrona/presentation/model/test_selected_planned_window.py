"""View-derived temporal breathing room does not mutate scheduled marks."""
from dataclasses import replace
from datetime import date, timedelta

import pytest

from chrona.presentation.contracts.resources import ViewRows
from chrona.presentation.layout.model import LayoutError
from chrona.presentation.layout.surface_base import prepare_surface_inline
from chrona.presentation.model.projection import ViewWindowError, build_review_projection
from tests.unit.chrona.presentation.model.test_projection_messages import _view
from tests.unit.chrona.presentation.layout.test_surface_slot_allocation import _request


@pytest.mark.parametrize(("days", "margin", "expected"), [
    (1, 0, 0), (11, 7, 7), (0, None, 1), (1, None, 1),
    (10, None, 1), (11, None, 2), (20, None, 2), (21, None, 3),
])
def test_selected_planned_uses_exact_authored_or_derived_padding(days, margin, expected):
    start = date(2027, 1, 4)
    end = start + timedelta(days=days)
    mark = {"at": start} if days == 0 else {"start": start, "end": end}
    view = _view(ViewRows("automatic", ()), window=("selected-planned", None, None, margin))
    projection = build_review_projection(
        {"objects": {"only": {"title": "Only"}}, "entities": {}}, {"only": mark}, view, None)
    intrinsic_end = start + timedelta(days=1 if days == 0 else days)
    assert projection.window == (start - timedelta(days=expected), intrinsic_end + timedelta(days=expected))
    assert projection.items[0].planned == mark


def test_zero_padding_point_has_a_positive_date_envelope():
    at = date(2027, 1, 4)
    view = _view(ViewRows("automatic", ()), window=("selected-planned", None, None, 0))
    projection = build_review_projection(
        {"objects": {"only": {"title": "Only"}}, "entities": {}}, {"only": {"at": at}}, view, None)
    assert projection.window == (at, at + timedelta(days=1))


def test_omitted_selected_comparison_padding_uses_mixed_half_open_envelope():
    start = date(2027, 1, 4)
    at = date(2027, 1, 20)
    view = _view(ViewRows("automatic", ()), window=("selected-comparison", None, None, None))
    project = {"objects": {"span": {"title": "Span"}, "point": {"title": "Point"}}, "entities": {}}
    placements = {"span": {"start": start, "end": start + timedelta(days=3)}, "point": {"at": at}}
    projection = build_review_projection(project, placements, view, None)
    assert projection.window == (start, at + timedelta(days=1))


@pytest.mark.parametrize("mode", ["explicit", "selected-comparison"])
def test_other_window_modes_keep_their_declared_contract(mode):
    view = _view(ViewRows("automatic", ()), window=(mode, "2027-01-01", "2027-02-01", 0))
    start, end = date(2027, 1, 4), date(2027, 1, 15)
    projection = build_review_projection(
        {"objects": {"only": {"title": "Only"}}, "entities": {}},
        {"only": {"start": start, "end": end}}, view, None)
    assert projection.window == ((date(2027, 1, 1), date(2027, 2, 1))
                                 if mode == "explicit" else (start, end))


@pytest.mark.parametrize(("at", "margin"), [(date.min, 1), (date.max, 0)])
def test_unrepresentable_window_names_dates_and_selected_object(at, margin):
    view = _view(ViewRows("automatic", ()), window=("selected-planned", None, None, margin))
    with pytest.raises(ValueError, match="E_REVIEW_WINDOW") as caught:
        build_review_projection({"objects": {"only": {"title": "Only"}}, "entities": {}},
                                {"only": {"at": at}}, view, None)
    assert isinstance(caught.value, ViewWindowError)
    assert caught.value.code == "E_REVIEW_WINDOW"
    assert str(at) in str(caught.value)
    assert "only" in str(caught.value)
    assert "Date domain" in str(caught.value)


def test_still_degenerate_layout_projection_has_owner_local_detail():
    request = _request()
    at = date(2027, 1, 4)
    request = replace(request, projection=replace(request.projection, window=(at, at)))
    with pytest.raises(LayoutError) as caught:
        prepare_surface_inline(request)
    assert caught.value.diagnostic_id == "E_PRESENTATION_PROJECTION_REQUIRED"
    assert caught.value.path == "/projection/window"
    assert "2027, 1, 4" in caught.value.detail
    assert "'a'" in caught.value.detail
    assert "positive Date window" in caught.value.detail
