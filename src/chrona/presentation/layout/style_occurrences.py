"""Join final surface aliases to source-owned Style occurrence identities."""
from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Mapping

from chrona.presentation.layout.lane_projection import close_lane_projection, lane_instance_owners
from chrona.presentation.layout.surface_mark_visibility import MarkOccurrence, MarkOccurrenceKind
from chrona.presentation.model.style_rules import StyleOccurrenceKey


@dataclass(frozen=True)
class StyleSourceOccurrences:
    """One immutable source join shared by mark and text composition."""

    has_rows: bool
    lane_mode: bool
    lane_sources: Mapping[tuple[str, str, str, str], MarkOccurrence]

    def __post_init__(self) -> None:
        object.__setattr__(self, "lane_sources", MappingProxyType(dict(self.lane_sources)))

    @classmethod
    def from_projection(cls, projection: Any, *, as_of: Any = None) -> StyleSourceOccurrences:
        sources = {}
        lane_mode = getattr(projection, "lane_membership", None) is not None
        if lane_mode:
            closure = close_lane_projection(projection, as_of=as_of)
            for instance, (lane_id, member_id) in lane_instance_owners(projection, closure).items():
                sources[(lane_id, member_id, instance.object_id, instance.source_kind)] = MarkOccurrence(
                    MarkOccurrenceKind.LANE_SOURCE, instance.row_id, instance.item_id,
                    instance.object_id, instance.source_kind)
        return cls(bool(projection.rows), lane_mode, MappingProxyType(sources))

    def occurrence(self, kind: MarkOccurrenceKind, container_id: str, member_id: str,
                   object_id: str, source_kind: str) -> MarkOccurrence:
        if kind == MarkOccurrenceKind.LANE_FINAL:
            return self.lane_sources[(container_id, member_id, object_id, source_kind)]
        return MarkOccurrence(kind, container_id, member_id, object_id, source_kind)

    def label_key(self, item: Any, container_id: str, semantic_id: str, *,
                  folded: bool = False) -> StyleOccurrenceKey:
        kind = (MarkOccurrenceKind.FOLDED if folded else MarkOccurrenceKind.LANE_FINAL
                if self.lane_mode else MarkOccurrenceKind.ROW if self.has_rows else MarkOccurrenceKind.AUTO)
        source_kind = item.source_kind if kind != MarkOccurrenceKind.AUTO else "combined"
        return self.occurrence(kind, container_id if kind != MarkOccurrenceKind.AUTO else item.object_id,
                               item.item_id or item.object_id, item.object_id, source_kind).style_key(semantic_id)
