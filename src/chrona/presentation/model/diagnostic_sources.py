"""Non-rendered producer provenance; never infer an owner from a drawing ID."""
from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Iterable
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from chrona.presentation.model.projection import ReviewRowProjection


@dataclass(frozen=True)
class DiagnosticSubject:
    source_ref: str
    title: str | None = None

    @classmethod
    def project_object(cls, object_id: str, title: str | None = None) -> DiagnosticSubject:
        escaped = object_id.replace("~", "~0").replace("/", "~1")
        return cls(f"/objects/{escaped}", title)


@dataclass(frozen=True)
class DiagnosticProvenance:
    """Subjects captured alongside one unchanged diagnostic occurrence."""

    diagnostic: str
    subjects: tuple[DiagnosticSubject, ...] = ()


@dataclass(frozen=True)
class PrimitiveProvenance:
    """An explicit primitive identity join, not a serialized Scene property."""

    primitive_id: str
    subjects: tuple[DiagnosticSubject, ...] = ()


def table_row_subjects(rows: Iterable[ReviewRowProjection]) -> dict[str, DiagnosticSubject]:
    """Resolve the declared table member, not a row ID or last comparison variant."""
    result = {}
    for row in rows:
        member = next((item for item in row.items
                       if (item.item_id or item.object_id) == row.table_subject_id), None)
        if member is not None:
            result[row.row_id] = DiagnosticSubject.project_object(member.object_id, member.title)
    return result


def review_row_subjects(rows: Iterable[ReviewRowProjection]) -> dict[str, tuple[DiagnosticSubject, ...]]:
    """A row-wide finding belongs to all explicitly selected Project members."""
    return {row.row_id: tuple(dict.fromkeys(DiagnosticSubject.project_object(item.object_id, item.title)
                                           for item in row.items)) for row in rows}
