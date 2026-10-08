"""Projection-only normalization of an already validated Review Detail Profile."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from collections.abc import Iterable

from chrona.presentation.contracts.resources import ReviewDetailInput


class ReviewDetailError(ValueError):
    """Stable Review Detail diagnostic."""


@dataclass(frozen=True)
class ResolvedReviewDetail:
    group_details: tuple[tuple[str, str, str], ...] = ()
    milestones: tuple[tuple[str, str, date], ...] = ()
    observation_columns: tuple[tuple[str, str], ...] = ()
    observation_rows: tuple[tuple[str, str, str, tuple[tuple[str, str], ...]], ...] = ()


def _unique(values: Iterable[str], diagnostic: str) -> None:
    materialized = tuple(values)
    if len(materialized) != len(set(materialized)):
        raise ReviewDetailError(diagnostic)


def normalize_v05_review_detail_profile(detail: ReviewDetailInput | None,
                                       items: Iterable[object]) -> ResolvedReviewDetail:
    """Resolve typed Detail facts against the selected projection once, without Layout knowledge."""
    selected = tuple(items)
    items_by_id = {str(getattr(item, "object_id")): item for item in selected}
    group_order = tuple(dict.fromkeys(str(getattr(item, "group_id", "")) for item in selected))

    group_values = tuple(detail.group_details) if detail is not None else ()
    _unique((str(entry["groupId"]) for entry in group_values), "E_DETAIL_DUPLICATE_GROUP")
    group_by_id = {str(entry["groupId"]): entry for entry in group_values}
    if any(group_id not in group_order for group_id in group_by_id):
        raise ReviewDetailError("E_DETAIL_GROUP_REFERENCE")
    groups = tuple((group_id, str(group_by_id[group_id]["label"]), str(group_by_id[group_id]["description"]))
                   for group_id in group_order if group_id in group_by_id)

    milestone_ids = tuple(str(value) for value in detail.milestones) if detail is not None else ()
    _unique(milestone_ids, "E_DETAIL_DUPLICATE_MILESTONE")
    milestones: list[tuple[str, str, date]] = []
    for object_id in milestone_ids:
        item = items_by_id.get(object_id)
        planned = getattr(item, "planned", {}) if item is not None else {}
        if item is None or str(getattr(item, "source_type", "")) != "point" or not isinstance(planned.get("at"), date):
            raise ReviewDetailError("E_DETAIL_MILESTONE_REFERENCE")
        milestones.append((object_id, str(getattr(item, "title", object_id)), planned["at"]))

    observation = detail.observations if detail is not None else None
    if observation is None:
        return ResolvedReviewDetail(groups, tuple(milestones))
    columns = tuple((str(entry["id"]), str(entry["label"])) for entry in observation["columns"])
    column_ids = tuple(column_id for column_id, _ in columns)
    _unique(column_ids, "E_DETAIL_DUPLICATE_COLUMN")
    row_values = observation["rows"]
    _unique((str(entry["id"]) for entry in row_values), "E_DETAIL_DUPLICATE_ROW")
    rows: list[tuple[str, str, str, tuple[tuple[str, str], ...]]] = []
    for entry in row_values:
        if set(entry["cells"]) != set(column_ids):
            raise ReviewDetailError("E_DETAIL_OBSERVATION_CELLS")
        source = str(entry["source"])
        if not source.strip():
            raise ReviewDetailError("E_DETAIL_OBSERVATION_PROVENANCE")
        cells = tuple((column_id, str(entry["cells"][column_id])) for column_id in column_ids)
        rows.append((str(entry["id"]), source, str(entry.get("emphasis", "normal")), cells))
    return ResolvedReviewDetail(groups, tuple(milestones), columns, tuple(rows))
