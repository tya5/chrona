"""#927: View gathers selected group dates without making Core own projection."""
from dataclasses import replace
from datetime import date

import pytest

from chrona.presentation.contracts import ClosureIdentity, parse_contract
from chrona.presentation.model.projection import ReviewItem, ReviewProjection, ReviewRowProjection
from chrona.usecases.render_review import RenderRejected, _resolved_group_figures
from tests.support import synthetic_review as sr

DAY = date(2028, 2, 28)
ACTUAL = {"body": {"asOf": DAY.isoformat()}}


def _view():
    value = sr.bundle("control-room-dark")["view"]
    value["body"]["figures"] = [{"id": "f", "kind": "daysUntil", "scope": "group",
                                "to": {"group": "firstPlannedStart"}}]
    identity = ClosureIdentity("view", value["id"], "r", "sha256:" + "a" * 64)
    return parse_contract(identity, value).view


def _item(object_id, group_id, at=DAY):
    return ReviewItem(object_id, object_id, "point", {"at": at}, None, None, (), group_id=group_id)


def _row(group_id, *items):
    return ReviewRowProjection("row-" + group_id, group_id, group_id, "", items)


def _resolve(items=(), rows=()):
    projection = ReviewProjection(items, (DAY, date(2028, 3, 2)), (), (), rows=rows)
    return _resolved_group_figures({}, {}, _view(), ACTUAL, projection)


def test_no_projected_group_is_a_declaration_diagnostic():
    with pytest.raises(RenderRejected) as failure:
        _resolve()
    assert [(d.id, d.path) for d in failure.value.diagnostics] == [
        ("E_FIGURE_GROUP_UNAVAILABLE", "/body/figures/0/scope")]


def test_empty_groups_report_every_missing_start_with_group_identity():
    with pytest.raises(RenderRejected) as failure:
        _resolve(rows=(_row("a"), _row("b")))
    assert [d.id for d in failure.value.diagnostics] == ["E_FIGURE_GROUP_START_MISSING"] * 2
    assert [d.message.split(":")[0] for d in failure.value.diagnostics] == ["Group a", "Group b"]


def test_combined_primary_rows_and_duplicates_do_not_change_group_membership():
    first = _item("first", "a")
    later = _item("later", "a", date(2028, 3, 1))
    combined = replace(first, source_kind="combined")
    ghost = replace(first, source_kind="snapshot", planned={"at": date(2028, 1, 1)})
    rows = (_row("a", combined, later, ghost), _row("a", combined))
    assert _resolve((first, later), rows) == (("a", (("f", 0),)),)


def test_comparison_only_group_does_not_implicitly_adopt_a_primary_start():
    primary = _item("first", "a")
    ghost = replace(primary, source_kind="snapshot")
    with pytest.raises(RenderRejected) as failure:
        _resolve((primary,), (_row("a", ghost),))
    assert failure.value.diagnostics[0].id == "E_FIGURE_GROUP_START_MISSING"


def test_selected_group_dates_resolve_independently_across_a_leap_boundary():
    a, b = _item("a", "a"), _item("b", "b", date(2028, 3, 1))
    assert _resolve((a, b), (_row("a", a), _row("b", b))) == (
        ("a", (("f", 0),)), ("b", (("f", 2),)))
