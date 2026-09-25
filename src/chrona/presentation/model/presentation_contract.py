"""Immutable normalized presentation semantics.

This is the one ingress boundary between current public presentation input and
Layout/Scene.  No legacy Settings or Theme objects are accepted here.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from chrona.presentation.model.surface_content import AnnotationIntent, AxisTier, RelationPresentationFact, SurfaceContentInput, TableCellContent, TableColumnContent


@dataclass(frozen=True)
class LabelContract:
    enabled: bool
    placement: str
    content: tuple[str, ...]
    side: str
    overflow: str


@dataclass(frozen=True)
class TimeContract:
    as_of: date | None
    as_of_label: str
    axis_tiers: tuple[AxisTier, ...]
    axis_fiscal_start_month: int
    calendar_closed: tuple[date, ...]
    calendar_exceptions: tuple[date, ...]


@dataclass(frozen=True)
class DecorationContract:
    legend_entries: tuple[tuple[str, str], ...]
    annotations: tuple[AnnotationIntent, ...]
    notes: tuple[tuple[str, str], ...]


@dataclass(frozen=True)
class PresentationContract:
    """Canonical presentation semantics consumed by later presentation stages."""

    table_columns: tuple[TableColumnContent, ...]
    table_cells: tuple[TableCellContent, ...]
    relations: tuple[RelationPresentationFact, ...]
    labels: LabelContract
    time: TimeContract
    decorations: DecorationContract
    source: SurfaceContentInput


def normalize_presentation_input(value: SurfaceContentInput) -> PresentationContract:
    """Normalize supported public aliases exactly once at presentation ingress."""
    labels_enabled = value.label_placement == "plot" or value.show_member_labels
    placement = "plot" if value.label_placement == "plot" else "none"
    label_content = value.label_content or (("title",) if labels_enabled else ())
    return PresentationContract(
        table_columns=value.table_columns,
        table_cells=value.table_cells,
        relations=value.relations,
        labels=LabelContract(labels_enabled, placement, label_content, value.label_side, value.label_overflow),
        time=TimeContract(value.as_of, value.as_of_label, value.axis_tiers,
                          value.axis_fiscal_start_month, value.calendar_closed, value.calendar_exceptions),
        decorations=DecorationContract(value.legend_entries, value.annotations, value.notes),
        source=value,
    )
