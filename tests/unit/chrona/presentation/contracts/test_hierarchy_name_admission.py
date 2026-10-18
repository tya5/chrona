from copy import deepcopy
from pathlib import Path

import pytest
import yaml

from chrona.presentation.contracts import ClosureIdentity, ContractError, parse_contract
from chrona.presentation.contracts.resources import SchemaContractError
from tests.support import synthetic_review as sr


ROOT = Path(__file__).resolve().parents[5]


def _parse(view):
    return parse_contract(
        ClosureIdentity("view", view["id"], "r", "sha256:" + "a" * 64), view,
    )


def _automatic_view():
    view = yaml.safe_load((ROOT / "examples/halcyon-1/views/06-flight-readiness.yaml").read_text(encoding="utf-8"))
    view["version"] = "chrona/view/v0.28"
    return view


def _lane_view():
    return sr.lane_view(sr.bundle("mission-light")["view"])


def _path_column(view):
    columns = view["body"].setdefault("tableColumns", [])
    template = deepcopy(next(column for column in columns if column["source"] == "title"))
    template["id"] = "Path"
    template["source"] = "path"
    columns.append(template)


def test_name_content_accepts_path_as_an_alternative_and_keeps_title_plus_path_column_valid():
    view = _automatic_view()
    view["body"]["tableColumns"] = [
        column for column in view["body"]["tableColumns"] if column["source"] == "title"
    ]
    _path_column(view)
    view["body"]["visibility"]["labels"] = {
        "placement": "both", "content": ["title", "finishDelta"], "side": "auto",
    }

    assert list(_parse(view).view.visibility.labels["content"]) == ["title", "finishDelta"]

    view["body"]["visibility"]["labels"] = {"placement": "both", "content": ["path"], "side": "auto"}
    assert list(_parse(view).view.visibility.labels["content"]) == ["path"]


def test_both_requires_the_selected_name_column_and_keeps_legacy_title_rule_for_delta_only():
    view = _automatic_view()
    title_columns = [column for column in view["body"]["tableColumns"] if column["source"] == "title"]
    view["body"]["tableColumns"] = title_columns
    view["body"]["visibility"]["labels"] = {"placement": "both", "content": ["path"], "side": "auto"}

    with pytest.raises(ContractError) as error:
        _parse(view)
    assert error.value.diagnostic_id == "E_VIEW_LABELS_BOTH_TABLE_TITLE"
    assert "source 'path'" in error.value.detail

    _path_column(view)
    assert list(_parse(view).view.visibility.labels["content"]) == ["path"]

    view["body"]["visibility"]["labels"] = {
        "placement": "both", "content": ["finishDelta"], "side": "auto",
    }
    assert list(_parse(view).view.visibility.labels["content"]) == ["finishDelta"]


@pytest.mark.parametrize("content", (["title", "path"], ["path", "title", "finishDelta"]))
def test_name_content_rejects_two_name_sources(content):
    view = _automatic_view()
    view["body"]["visibility"]["labels"] = {"placement": "plot", "content": content, "side": "auto"}

    with pytest.raises(SchemaContractError, match="E_RESOURCE_SCHEMA"):
        _parse(view)


def test_non_lane_delta_only_remains_valid_but_lane_path_is_a_valid_name_source():
    view = _automatic_view()
    view["body"]["visibility"]["labels"] = {
        "placement": "plot", "content": ["finishDelta"], "side": "auto",
    }
    assert list(_parse(view).view.visibility.labels["content"]) == ["finishDelta"]

    lane = _lane_view()
    lane["body"]["visibility"]["labels"]["content"] = ["path", "finishDelta"]
    assert list(_parse(lane).view.visibility.labels["content"]) == ["path", "finishDelta"]

    lane["body"]["visibility"]["labels"]["content"] = ["finishDelta"]
    with pytest.raises(SchemaContractError, match="E_RESOURCE_SCHEMA"):
        _parse(lane)


def test_omitted_lane_content_keeps_its_existing_default_admission():
    lane = _lane_view()
    assert _parse(lane).view.visibility.labels["placement"] == "plot"
