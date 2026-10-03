"""`hierarchyColumn` under field grouping shown as headers (#1065): the View contract, on a synthetic packaged View."""
import pytest

from chrona.presentation.contracts import ClosureIdentity, ContractError, parse_contract
from tests.support import synthetic_review as sr

COLUMN = "Work item"


def _view(*, presentation: str | None = "header", by: str = "field", column: str | None = COLUMN) -> dict:
    view = sr.bundle("executive-light")["view"]
    body = view["body"]
    body["rows"] = {"mode": "automatic"}
    body["tableColumns"] = [{"id": COLUMN, "source": "title", "missing": "em-dash", "align": "start",
                             "width": {"fr": 1}, "headerOrientation": "horizontal"}]
    if presentation is None:
        body["grouping"].pop("presentation")
    else:
        body["grouping"]["presentation"] = presentation
    if by != "field":
        body["grouping"] = {"by": by, "depth": 1, "rollup": "header", "presentation": presentation}
    if column is not None:
        body["hierarchyColumn"] = column
    return view


def _parse(view):
    return parse_contract(ClosureIdentity("view", view["id"], "r", "sha256:" + "a" * 64), view)


def test_a_hierarchy_column_is_accepted_under_field_grouping_with_headers():
    assert _parse(_view()).view.hierarchy_column == COLUMN


@pytest.mark.parametrize("presentation", ["band", None])
def test_it_is_still_unexpected_without_headers(presentation):
    with pytest.raises(ContractError, match="E_VIEW_HIERARCHY_COLUMN_UNEXPECTED") as raised:
        _parse(_view(presentation=presentation))
    assert "field grouping with presentation header" in raised.value.detail


def test_a_view_without_the_declaration_is_unchanged():
    assert _parse(_view(column=None)).view.hierarchy_column is None


def test_hierarchy_grouping_still_requires_the_declaration():
    with pytest.raises(ContractError, match="E_VIEW_HIERARCHY_COLUMN_REQUIRED"):
        _parse(_view(by="hierarchy", column=None))
