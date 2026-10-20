"""Projection of Layout's completed original-mark omissions onto lane members."""
from __future__ import annotations

from typing import TYPE_CHECKING

from chrona.presentation.scene.model import SceneLaneRowAbsence, SceneLaneWindowAbsence

if TYPE_CHECKING:
    from chrona.presentation.layout.lane_window_marks import (
        LaneWindowPlacementAbsence, LaneWindowRowAbsence,
    )


def project_lane_window_absences(
    absences: tuple[LaneWindowPlacementAbsence, ...],
) -> dict[tuple[str, str], tuple[SceneLaneWindowAbsence, ...]]:
    """Copy the supplied final owner and opaque source identity, never infer either."""
    grouped: dict[tuple[str, str], list[SceneLaneWindowAbsence]] = {}
    for absence in absences:
        expected = absence.expected
        original = expected.instance
        projected = SceneLaneWindowAbsence(
            expected.placement_id, original.placement_key, expected.purpose,
            absence.source_ref, original.source_kind, expected.role, absence.reason)
        grouped.setdefault((absence.row_id, absence.member_id), []).append(projected)
    return {owner: tuple(values) for owner, values in grouped.items()}


def project_lane_window_row_absences(
    absences: tuple[LaneWindowRowAbsence, ...],
) -> dict[tuple[str, str], SceneLaneRowAbsence]:
    """Project Layout's completed per-member row reason without its cache."""
    grouped: dict[tuple[str, str], SceneLaneRowAbsence] = {}
    row_reasons: dict[str, str] = {}
    for absence in absences:
        key = (absence.row_id, absence.member_id)
        previous = grouped.get(key)
        prior_reason = row_reasons.get(absence.row_id)
        projected = SceneLaneRowAbsence(absence.reason)
        if (previous is not None or prior_reason not in {None, absence.reason}):
            raise ValueError("E_PRESENTATION_PRIMITIVE_INVALID: duplicate or conflicting lane row absence")
        grouped[key] = projected
        row_reasons[absence.row_id] = absence.reason
    return grouped
