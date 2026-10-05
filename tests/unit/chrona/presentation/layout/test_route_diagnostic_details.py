import pytest

from chrona.presentation.layout.route_search import (
    RouteSearchFailure,
    orthogonal_route_candidates,
)
from chrona.presentation.layout.routing import RouteAttemptEvidence


def test_route_search_input_error_identifies_required_fields():
    with pytest.raises(ValueError, match="E_LAYOUT_ROUTE_SEARCH_INPUT:.*finite 2D points"):
        tuple(orthogonal_route_candidates((0,), (2, 0), ()))


def test_route_search_failure_keeps_stable_code_string_and_exposes_detail():
    with pytest.raises(RouteSearchFailure, match="^E_CONNECTOR_UNROUTABLE$") as caught:
        tuple(orthogonal_route_candidates(
            (0, 0), (2, 0), (), bounds=(0, 0, 1, 1)))

    assert caught.value.detail == "The supplied bounds exclude the start or end point."
    assert str(RouteSearchFailure(str(caught.value))) == "E_CONNECTOR_UNROUTABLE"


def test_route_attempt_disposition_error_names_allowed_values():
    with pytest.raises(ValueError, match="E_LAYOUT_ROUTE_ATTEMPT_INVALID:.*bounded-candidates-exhausted.*expansion-limit"):
        RouteAttemptEvidence(
            "left", "right", "quality-rejected", length=1, direct_length=1,
            bends=0, max_bends=0, max_detour_ratio=2, search_disposition="unknown")
