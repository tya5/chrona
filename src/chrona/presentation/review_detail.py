"""M23 Review Detail Profile validation and projection-only resolution."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, Iterable, Mapping

import yaml
from jsonschema import Draft202012Validator


PROFILE_VERSION = "chrona/review-detail-profile/v0.1"
_ROOT = Path(__file__).resolve().parents[3]
_SCHEMA = _ROOT / "schemas/review-detail-profile-v0.1.schema.yaml"
_PANEL_SOURCES = {
    "groupDetails": "group-details",
    "milestones": "milestones",
    "observations": "observations",
}


class ReviewDetailError(ValueError):
    """Stable Review Detail diagnostic."""


@dataclass(frozen=True)
class ResolvedReviewDetail:
    group_details: tuple[tuple[str, str, str], ...] = ()
    milestones: tuple[tuple[str, str, date], ...] = ()
    observation_columns: tuple[tuple[str, str], ...] = ()
    observation_rows: tuple[tuple[str, str, str, tuple[tuple[str, str], ...]], ...] = ()


def _validate_shape(profile: Mapping[str, Any]) -> None:
    schema = yaml.safe_load(_SCHEMA.read_text(encoding="utf-8"))
    if next(Draft202012Validator(schema).iter_errors(dict(profile)), None) is not None:
        raise ReviewDetailError("E_DETAIL_PROFILE_SCHEMA")


def _unique(values: Iterable[str], diagnostic: str) -> None:
    materialized = tuple(values)
    if len(materialized) != len(set(materialized)):
        raise ReviewDetailError(diagnostic)


def _validate_slots(body: Mapping[str, Any], settings: Mapping[str, Any]) -> None:
    slots = settings["layout"]["slots"]
    for key, source in _PANEL_SOURCES.items():
        matching = [(slot_id, slot) for slot_id, slot in slots.items() if slot["source"] == source]
        if len(matching) > 1:
            raise ReviewDetailError(f"E_DETAIL_SLOT_DUPLICATE:{source}")
        if key in body and not matching:
            raise ReviewDetailError(f"E_DETAIL_SLOT_REQUIRED:{source}")
        if key not in body and matching and matching[0][1]["priority"] == "required":
            raise ReviewDetailError(f"E_LAYOUT_SOURCE_UNAVAILABLE:{matching[0][0]}")


def resolve_review_detail_profile(profile: Mapping[str, Any] | None, items: Iterable[object],
                                  settings: Mapping[str, Any]) -> ResolvedReviewDetail:
    """Validate and normalize detail content without adding scheduling authority."""
    if profile is None:
        _validate_slots({}, settings)
        return ResolvedReviewDetail()
    _validate_shape(profile)
    body = profile["body"]
    _validate_slots(body, settings)
    selected = tuple(items)
    items_by_id = {str(getattr(item, "object_id")): item for item in selected}
    group_order = tuple(dict.fromkeys(str(getattr(item, "group_id", "")) for item in selected))

    group_values = body.get("groupDetails", ())
    _unique((str(entry["groupId"]) for entry in group_values), "E_DETAIL_DUPLICATE_GROUP")
    group_by_id = {str(entry["groupId"]): entry for entry in group_values}
    if any(group_id not in group_order for group_id in group_by_id):
        raise ReviewDetailError("E_DETAIL_GROUP_REFERENCE")
    groups = tuple((group_id, str(group_by_id[group_id]["label"]),
                    str(group_by_id[group_id]["description"]))
                   for group_id in group_order if group_id in group_by_id)

    milestone_ids = tuple(str(value) for value in body.get("milestones", ()))
    _unique(milestone_ids, "E_DETAIL_DUPLICATE_MILESTONE")
    milestones = []
    for object_id in milestone_ids:
        item = items_by_id.get(object_id)
        planned = getattr(item, "planned", {}) if item is not None else {}
        if item is None or str(getattr(item, "source_type", "")) != "point" or not isinstance(planned.get("at"), date):
            raise ReviewDetailError("E_DETAIL_MILESTONE_REFERENCE")
        milestones.append((object_id, str(getattr(item, "title", object_id)), planned["at"]))

    observation = body.get("observations")
    if observation is None:
        columns = ()
        rows = ()
    else:
        columns = tuple((str(entry["id"]), str(entry["label"])) for entry in observation["columns"])
        column_ids = tuple(column_id for column_id, _ in columns)
        _unique(column_ids, "E_DETAIL_DUPLICATE_COLUMN")
        row_values = observation["rows"]
        _unique((str(entry["id"]) for entry in row_values), "E_DETAIL_DUPLICATE_ROW")
        rows_list = []
        for entry in row_values:
            if set(entry["cells"]) != set(column_ids):
                raise ReviewDetailError("E_DETAIL_OBSERVATION_CELLS")
            source = str(entry["source"])
            if not source.strip():
                raise ReviewDetailError("E_DETAIL_OBSERVATION_PROVENANCE")
            cells = tuple((column_id, str(entry["cells"][column_id])) for column_id in column_ids)
            rows_list.append((str(entry["id"]), source, str(entry.get("emphasis", "normal")), cells))
        rows = tuple(rows_list)
    return ResolvedReviewDetail(groups, tuple(milestones), columns, rows)
