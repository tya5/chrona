from copy import deepcopy

import pytest

from chrona.presentation.contracts import ClosureIdentity, ContractError, parse_contract
from tests.support import synthetic_review as sr


def _parse(value):
    return parse_contract(ClosureIdentity("view", value["id"], "test", "sha256:" + "a" * 64), value)


def _view():
    view = deepcopy(sr.bundle("control-room-dark")["view"])
    view["version"] = "chrona/view/v0.28"
    return view


@pytest.mark.parametrize(("window", "expected"), [
    ({"mode": "relative", "before": "2d", "after": "1w"}, ("2d", "1w", "keep")),
    ({"mode": "relative", "after": "0d", "outside": "omit", "before": "1w"}, ("1w", "0d", "omit")),
])
def test_v028_relative_window_and_completion_filter_are_typed(window, expected):
    value = _view()
    value["body"]["window"] = window
    value["body"]["selection"] = {"include": {}, "exclude": {"state": ["finished"]}}

    contract = _parse(value)

    assert (contract.view.window.before, contract.view.window.after, contract.view.window.outside) == expected
    assert contract.view.selection.excluded_states == ("finished",)


@pytest.mark.parametrize("window", [
    {"mode": "relative"},
    {"mode": "relative", "before": "0d", "after": "0w"},
    {"mode": "relative", "before": "-1d"},
    {"mode": "relative", "after": "01d"},
    {"mode": "relative", "before": "1d", "start": "2026-01-01"},
    {"mode": "relative", "after": "1w", "marginDays": 1},
    {"mode": "selected-planned", "before": "1d"},
    {"mode": "selected-comparison", "outside": "omit"},
])
def test_v028_window_rejects_incomplete_or_mode_conflicting_declarations(window):
    value = _view()
    value["body"]["window"] = window

    with pytest.raises(ContractError, match="E_RESOURCE_SCHEMA"):
        _parse(value)


def test_finished_completion_state_is_closed_and_relative_window_is_timeline_only():
    value = _view()
    value["body"]["selection"] = {"include": {}, "exclude": {"state": ["forecasted"]}}
    with pytest.raises(ContractError, match="E_RESOURCE_SCHEMA"):
        _parse(value)

    value = _view()
    value["body"]["surface"] = "dependency-network"
    value["body"]["window"] = {"mode": "relative", "before": "1w"}
    with pytest.raises(ContractError, match="E_RESOURCE_SCHEMA"):
        _parse(value)
