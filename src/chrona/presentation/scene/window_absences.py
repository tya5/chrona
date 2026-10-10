"""Projection of Layout's completed original-mark omissions onto lane members."""
from __future__ import annotations

from typing import TYPE_CHECKING

from chrona.presentation.scene.model import SceneLaneWindowAbsence

if TYPE_CHECKING:
    from chrona.presentation.layout.lane_window_marks import LaneWindowPlacementAbsence


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
