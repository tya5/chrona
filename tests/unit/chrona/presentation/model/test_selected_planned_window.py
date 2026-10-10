"""View-derived temporal breathing room does not mutate scheduled marks."""
from dataclasses import replace
from datetime import date, timedelta

import pytest

from chrona.presentation.contracts.resources import ViewRows
from chrona.presentation.layout.model import LayoutError
from chrona.presentation.layout.surface_base import prepare_surface_inline
from chrona.presentation.model.projection import build_review_projection
from tests.unit.chrona.presentation.model.test_projection_messages import _view
from tests.unit.chrona.presentation.layout.test_surface_slot_allocation import _request


@pytest.mark.parametrize(("days", "margin", "expected"), [
    (0, 0, 1), (1, 0, 1), (10, 0, 1), (11, 0, 2),
    (20, 0, 2), (21, 0, 3), (11, 7, 7),
])
def test_selected_planned_pads_each_side_without_changing_marks(days, margin, expected):
    start = date(2027, 1, 4)
    end = start + timedelta(days=days)
    mark = {"at": start} if days == 0 else {"start": start, "end": end}
    view = _view(ViewRows("automatic", ()), window=("selected-planned", None, None, margin))
    projection = build_review_projection(
        {"objects": {"only": {"title": "Only"}}, "entities": {}}, {"only": mark}, view, None)
    assert projection.window == (start - timedelta(days=expected), end + timedelta(days=expected))
    assert projection.items[0].planned == mark


@pytest.mark.parametrize("mode", ["explicit", "selected-comparison"])
def test_other_window_modes_keep_their_declared_contract(mode):
    view = _view(ViewRows("automatic", ()), window=(mode, "2027-01-01", "2027-02-01", 0))
    start, end = date(2027, 1, 4), date(2027, 1, 15)
    projection = build_review_projection(
        {"objects": {"only": {"title": "Only"}}, "entities": {}},
        {"only": {"start": start, "end": end}}, view, None)
    assert projection.window == ((date(2027, 1, 1), date(2027, 2, 1))
                                 if mode == "explicit" else (start, end))


@pytest.mark.parametrize("at", [date.min, date.max])
def test_unrepresentable_padding_names_dates_and_selected_object(at):
    view = _view(ViewRows("automatic", ()))
    with pytest.raises(ValueError, match="E_REVIEW_WINDOW") as caught:
        build_review_projection({"objects": {"only": {"title": "Only"}}, "entities": {}},
                                {"only": {"at": at}}, view, None)
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
