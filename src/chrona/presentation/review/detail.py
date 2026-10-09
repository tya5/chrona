"""Projection-only normalization of an already validated Review Detail Profile."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from collections.abc import Iterable

from chrona.presentation.contracts.resources import ReviewDetailInput


class ReviewDetailError(ValueError):
    """Stable Review Detail diagnostic."""


def _shown(value: object) -> str:
    """Show bounded identifier/source operands without dumping review content."""
    if isinstance(value, (str, int, float, bool, type(None))):
        text = repr(value)
        return text if len(text) <= 96 else text[:93] + "..."
    if isinstance(value, (tuple, list)):
        parts = [_shown(part) for part in value[:8]]
        suffix = ", ..." if len(value) > 8 else ""
        return "[" + ", ".join(parts) + suffix + "]"
    return f"<{type(value).__name__}>"


@dataclass(frozen=True)
class ResolvedReviewDetail:
    group_details: tuple[tuple[str, str, str], ...] = ()
    milestones: tuple[tuple[str, str, date], ...] = ()
    observation_columns: tuple[tuple[str, str], ...] = ()
    observation_rows: tuple[tuple[str, str, str, tuple[tuple[str, str], ...]], ...] = ()


def _unique(values: Iterable[str], diagnostic: str, *, field: str) -> None:
    materialized = tuple(values)
    first_ordinal: dict[str, int] = {}
    for ordinal, value in enumerate(materialized, start=1):
        if value in first_ordinal:
            raise ReviewDetailError(
                f"{diagnostic}: {field}={_shown(value)} repeats at ordinal={ordinal}; firstOrdinal={first_ordinal[value]}"
            )
        first_ordinal[value] = ordinal


def normalize_v05_review_detail_profile(detail: ReviewDetailInput | None,
                                       items: Iterable[object]) -> ResolvedReviewDetail:
    """Resolve typed Detail facts against the selected projection once, without Layout knowledge."""
    selected = tuple(items)
    items_by_id = {str(getattr(item, "object_id")): item for item in selected}
    group_order = tuple(dict.fromkeys(str(getattr(item, "group_id", "")) for item in selected))

    group_values = tuple(detail.group_details) if detail is not None else ()
    _unique((str(entry["groupId"]) for entry in group_values), "E_DETAIL_DUPLICATE_GROUP",
            field="/groupDetails/groupId")
    group_by_id = {str(entry["groupId"]): entry for entry in group_values}
    unknown_group = next((group_id for group_id in group_by_id if group_id not in group_order), None)
    if unknown_group is not None:
        raise ReviewDetailError(
            f"E_DETAIL_GROUP_REFERENCE: /groupDetails/groupId={_shown(unknown_group)} is not selected; selectedGroups={_shown(group_order)}"
        )
    groups = tuple((group_id, str(group_by_id[group_id]["label"]), str(group_by_id[group_id]["description"]))
                   for group_id in group_order if group_id in group_by_id)

    milestone_ids = tuple(str(value) for value in detail.milestones) if detail is not None else ()
    _unique(milestone_ids, "E_DETAIL_DUPLICATE_MILESTONE", field="/milestones")
    milestones: list[tuple[str, str, date]] = []
    for object_id in milestone_ids:
        item = items_by_id.get(object_id)
        planned = getattr(item, "planned", {}) if item is not None else {}
        if item is None:
            raise ReviewDetailError(f"E_DETAIL_MILESTONE_REFERENCE: /milestones objectId={_shown(object_id)} is not selected")
        source_type = str(getattr(item, "source_type", ""))
        if source_type != "point":
            raise ReviewDetailError(f"E_DETAIL_MILESTONE_REFERENCE: /objects/{_shown(object_id)} sourceType={_shown(source_type)}; expected point")
        if not isinstance(planned.get("at"), date):
            at = planned.get("at")
            raise ReviewDetailError(f"E_DETAIL_MILESTONE_REFERENCE: /objects/{_shown(object_id)}/planned/at={_shown(at)} ({type(at).__name__}); expected a date")
        milestones.append((object_id, str(getattr(item, "title", object_id)), planned["at"]))

    observation = detail.observations if detail is not None else None
    if observation is None:
        return ResolvedReviewDetail(groups, tuple(milestones))
    columns = tuple((str(entry["id"]), str(entry["label"])) for entry in observation["columns"])
    column_ids = tuple(column_id for column_id, _ in columns)
    _unique(column_ids, "E_DETAIL_DUPLICATE_COLUMN", field="/observations/columns/id")
    row_values = observation["rows"]
    _unique((str(entry["id"]) for entry in row_values), "E_DETAIL_DUPLICATE_ROW",
            field="/observations/rows/id")
    rows: list[tuple[str, str, str, tuple[tuple[str, str], ...]]] = []
    for entry in row_values:
        actual_cells, expected_cells = set(entry["cells"]), set(column_ids)
        if actual_cells != expected_cells:
            missing = sorted(expected_cells - actual_cells)
            unexpected = sorted(actual_cells - expected_cells)
            raise ReviewDetailError(
                f"E_DETAIL_OBSERVATION_CELLS: /observations/rows/{_shown(entry['id'])}/cells has missing={_shown(missing[:8])}, unexpected={_shown(unexpected[:8])}; expected column ids={_shown(sorted(expected_cells)[:8])}"
            )
        source = str(entry["source"])
        if not source.strip():
            raise ReviewDetailError(
                f"E_DETAIL_OBSERVATION_PROVENANCE: /observations/rows/{_shown(entry['id'])}/source={_shown(source)} must be nonblank provenance text"
            )
        cells = tuple((column_id, str(entry["cells"][column_id])) for column_id in column_ids)
        rows.append((str(entry["id"]), source, str(entry.get("emphasis", "normal")), cells))
    return ResolvedReviewDetail(groups, tuple(milestones), columns, tuple(rows))
