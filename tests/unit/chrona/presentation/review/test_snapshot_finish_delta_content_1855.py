from dataclasses import replace
from datetime import date

from chrona.core.forecast import ForecastItem
from chrona.presentation.contracts.resources import (
    TableColumn, ViewComparison, ViewInput, ViewRows, ViewVisibility, ViewWindow, freeze,
)
from chrona.presentation.model.projection import ForecastComparisonFact, ReviewItem, ReviewProjection
from chrona.presentation.model.surface_content import table_value
from chrona.presentation.review.v05_content import normalize_v05_table_content


def _column(identifier, source, *, header=None, wording=False, missing="em-dash"):
    return TableColumn(
        identifier, freeze(source), "signedDays", missing,
        header=freeze({"wording": "column.finishDelta"}) if wording else header,
        header_wording_key="column.finishDelta" if wording else None,
    )


def _view(*columns, wording=None):
    return ViewInput(
        None, None, None, ViewWindow("selected-planned", None, None, 0),
        ViewComparison(None, "optional", None, None, ()),
        ViewVisibility(False, "none", "none"), tuple(columns), (), ViewRows("automatic", ()),
        None, (), None, None, None, wording=freeze(wording) if wording is not None else None,
    )


def _item(identifier="a", *, snapshot_delta=None, ordinary_delta=None, new=False, forecast=None):
    return ReviewItem(
        identifier, identifier, "point", {"at": date(2026, 1, 5)}, None,
        ordinary_delta, (), snapshot_finish_delta=snapshot_delta,
        new_vs_baseline=new, new_marker="new", forecast=forecast,
    )


def _projection(*items, snapshot=True):
    return ReviewProjection(
        tuple(items), (date(2026, 1, 1), date(2026, 1, 10)), (), (),
        bound_comparison_sources=frozenset({"snapshot"} if snapshot else ()),
    )


def test_snapshot_delta_column_needs_snapshot_only_and_uses_baseline_header():
    projection = _projection(_item(snapshot_delta=4))
    snapshot_column = _column("Snapshot", {"comparisonFacet": "snapshotFinishDelta"}, wording=True)
    ordinary_column = _column("Ordinary", {"comparisonFacet": "finishDelta"})

    table = normalize_v05_table_content(projection, {}, _view(snapshot_column, ordinary_column))

    assert [column.column_id for column in table.columns] == ["Snapshot"]
    assert table.columns[0].header == "Δ vs baseline"
    assert table.cells[0].content == "+4d"

    absent = normalize_v05_table_content(_projection(_item(snapshot_delta=4), snapshot=False), {},
                                         _view(snapshot_column))
    assert absent.columns == ()
    assert absent.cells == ()


def test_snapshot_and_ordinary_delta_coexist_without_sharing_estimate_marker():
    forecast = ForecastComparisonFact(
        ForecastItem({"start": date(2026, 1, 1), "finish": date(2026, 1, 10)}, completed=False), 5)
    item = _item(snapshot_delta=4, ordinary_delta=2, forecast=forecast)
    table = normalize_v05_table_content(
        _projection(item), {}, _view(
            _column("Snapshot", {"comparisonFacet": "snapshotFinishDelta"}),
            _column("Ordinary", {"comparisonFacet": "finishDelta"}),
        ),
    )

    assert [(cell.column_id, cell.content, cell.semantic_id) for cell in table.cells] == [
        ("Snapshot", "+4d", "tableCell"),
        ("Ordinary", "+5d*", "tableVarianceBehind"),
    ]
    assert [cell.required for cell in table.cells] == [False, True]


def test_new_point_uses_snapshot_column_missing_policy_without_changing_ordinary_new_marker():
    item = _item(new=True)
    table = normalize_v05_table_content(
        _projection(item), {}, _view(
            _column("Snapshot", {"comparisonFacet": "snapshotFinishDelta"}),
            _column("Ordinary", {"comparisonFacet": "finishDelta"}),
        ),
        actual_set={"body": {"observations": []}},
    )

    assert [(cell.column_id, cell.content) for cell in table.cells] == [
        ("Snapshot", "—"),
        ("Ordinary", "new"),
    ]


def test_snapshot_header_wording_override_and_literal_header_remain_authored():
    projection = _projection(_item(snapshot_delta=1))
    authored = _column("Delta", {"comparisonFacet": "snapshotFinishDelta"}, wording=True)
    override = _view(authored, wording={"keys": {"column.finishDelta": "Snapshot movement"}})
    assert normalize_v05_table_content(projection, {}, override).columns[0].header == "Snapshot movement"

    literal = _column("Delta", {"comparisonFacet": "snapshotFinishDelta"}, header="Period movement")
    assert normalize_v05_table_content(projection, {}, _view(literal)).columns[0].header == "Period movement"


def test_snapshot_delta_value_is_primary_track_only():
    source = {"comparisonFacet": "snapshotFinishDelta"}
    for source_kind in ("snapshot", "scenario", "actual"):
        item = replace(_item(snapshot_delta=7), source_kind=source_kind)
        assert table_value(item, {}, source) is None
