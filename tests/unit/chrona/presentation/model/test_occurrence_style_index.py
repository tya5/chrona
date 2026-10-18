"""Occurrence-scoped Style intent carriers keep source identities immutable."""
from dataclasses import FrozenInstanceError

import pytest

from chrona.presentation.model.style_rules import (
    OccurrenceStyleIndex, OccurrenceStyleIntent, StyleEvaluationError, StyleOccurrenceKey,
)
from chrona.presentation.model.surface_content import (
    SurfaceContentInput, TableCellContent, TableColumnContent, TableColumnWidth, SummaryContent,
)


def _intent(key: StyleOccurrenceKey, role: str | None = "planned") -> OccurrenceStyleIntent:
    return OccurrenceStyleIntent(key, role, None, ("rule",), ("rule",) if role else (), ())


def _key(*, semantic: str = "planned", occurrence_kind: str = "row", column_id: str = "") -> StyleOccurrenceKey:
    return StyleOccurrenceKey("subject", "primary", semantic, "row", "member", column_id, occurrence_kind)


def test_style_index_detaches_input_sequence_and_exposes_immutable_lookups():
    key = _key()
    intents = [_intent(key)]

    index = OccurrenceStyleIndex(intents)
    intents.append(_intent(_key(semantic="forecast")))

    assert index.intents == (_intent(key),)
    assert index.get(key) == _intent(key)
    assert index.get(_key(semantic="forecast")) is None
    with pytest.raises(TypeError):
        index._by_key[key] = _intent(key, None)


def test_duplicate_style_intent_keys_use_existing_conflict_error():
    key = _key()

    with pytest.raises(StyleEvaluationError) as error:
        OccurrenceStyleIndex((_intent(key), _intent(key, None)))

    assert error.value.diagnostic_id == "E_STYLE_RULE_CONFLICT"
    assert error.value.subject == key


def test_occurrence_kind_is_part_of_identity_and_semantics_group_under_exact_source_key():
    planned = _key()
    forecast = _key(semantic="forecast")
    folded = _key(semantic="planned", occurrence_kind="folded")
    other_column = _key(semantic="planned", column_id="owner")
    index = OccurrenceStyleIndex(tuple(_intent(key) for key in (planned, forecast, folded, other_column)))

    assert planned != folded
    assert index.for_occurrence(forecast) == {"planned": _intent(planned), "forecast": _intent(forecast)}
    assert index.for_occurrence(folded) == {"planned": _intent(folded)}
    assert index.for_occurrence(other_column) == {"planned": _intent(other_column)}
    with pytest.raises(TypeError):
        index.for_occurrence(planned)["actual"] = _intent(_key(semantic="actual"))
    assert index.for_occurrence(_key(occurrence_kind="missing")) == {}


def test_surface_carrier_defaults_preserve_existing_cell_and_column_construction():
    cell = TableCellContent("subject", "title", "Subject", "tableCell")
    column = TableColumnContent("title", "Title", "start", TableColumnWidth("content", "content"))
    surface = SurfaceContentInput(
        table_columns=(), table_cells=(), relations=(), annotations=(), show_member_labels=False,
        label_placement="plot", label_content=(), label_side="end", label_overflow="suppress",
        relation_overflow="none", group_presentation="none", axis_tiers=(), axis_fiscal_start_month=1,
        as_of=None, as_of_label="", annotation_numbered=False, calendar_closed=(), calendar_exceptions=(),
        notes=(), legend_entries=(), coverage_text="", summary=SummaryContent(()), template_values=(),
        group_details=(), milestones=(), observation_columns=(), observation_rows=(),
    )

    assert cell.style_key is None
    assert column.column_source is None
    assert surface.style_intents == OccurrenceStyleIndex()
    with pytest.raises(FrozenInstanceError):
        cell.style_key = _key()


def test_table_column_source_is_detached_as_immutable_exact_pairs():
    source = {"field": "owner"}
    column = TableColumnContent(
        "owner", "Owner", "start", TableColumnWidth("content", "content"), column_source=source,
    )
    source["field"] = "phase"

    assert column.column_source == (("field", "owner"),)
    assert isinstance(column.column_source, tuple)
