"""Collect immutable, source-keyed Style facts before Layout composition."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from chrona.presentation.model.mark_semantics import canonical_mark_semantic
from chrona.presentation.model.hierarchy_names import member_name_key
from chrona.presentation.model.projection import (
    ReviewProjection,
    display_finish_delta,
    finish_delta_semantic,
)
from chrona.presentation.model.semantic_mark_facets import select_item_mark_facets
from chrona.presentation.model.semantic_registry import (
    inside_member_label_semantic,
    semantic_binding,
)
from chrona.presentation.model.style_rules import (
    StyleFieldFact,
    StyleOccurrence,
    StyleOccurrenceKey,
    field_facts_for_item,
)
from chrona.presentation.model.surface_content import SurfaceContentInput


@dataclass(frozen=True)
class SurfaceStyleFacts:
    """One immutable source snapshot for Style evaluation."""

    occurrences: tuple[StyleOccurrence, ...]
    field_catalogue: tuple[StyleFieldFact, ...]


@dataclass(frozen=True)
class _SourceItem:
    item: Any
    row_id: str
    occurrence_kind: str
    source_kind: str
    content_container_id: str
    key_row: bool = False

    @property
    def member_id(self) -> str:
        return self.item.item_id or self.item.object_id

    def key(self, semantic_id: str) -> StyleOccurrenceKey:
        return StyleOccurrenceKey(
            self.item.object_id,
            self.source_kind,
            semantic_id,
            self.row_id,
            self.member_id,
            occurrence_kind=self.occurrence_kind,
        )


def _source_items(projection: ReviewProjection) -> tuple[_SourceItem, ...]:
    items: list[_SourceItem] = []
    if projection.rows:
        occurrence_kind = "lane-source" if projection.lane_membership is not None else "row"
        lane_by_row = {}
        if projection.lane_membership is not None:
            lane_by_member = {
                member_id: lane.lane_id
                for lane in projection.lane_rows
                for member_id in lane.member_item_ids
            }
            lane_by_row = {
                row.row_id: lane_by_member.get(
                    row.items[0].item_id or row.items[0].object_id, row.row_id)
                for row in projection.rows if row.items
            }
        for row in projection.rows:
            for item in row.items:
                items.append(_SourceItem(item, row.row_id, occurrence_kind, item.source_kind,
                                         lane_by_row.get(row.row_id, row.row_id),
                                         bool(getattr(row, "key_row", False))))
    elif not projection.rows_resolved:
        # Legacy direct projections have no normalized rows. Match Layout's
        # automatic occurrence source kind and leave row identity empty.
        items.extend(_SourceItem(item, "", "auto", "combined", "")
                     for item in projection.items)

    for folded in projection.folded_points:
        items.extend(_SourceItem(item, folded.group_id, "folded", item.source_kind, folded.group_id)
                     for item in folded.all_items)
    return tuple(items)


def _all_source_items(projection: ReviewProjection) -> tuple[Any, ...]:
    """Return source items once for declarations, including unselected projection items."""
    candidates = [*projection.items]
    candidates.extend(item for row in projection.rows for item in row.items)
    candidates.extend(item for row in projection.lane_rows for item in row.items)
    candidates.extend(item for folded in projection.folded_points for item in folded.all_items)
    return tuple(candidates)


def _field_catalogue(items: tuple[Any, ...]) -> tuple[StyleFieldFact, ...]:
    """Collect declarations from every source binding, not current values alone."""
    catalogue: list[StyleFieldFact] = []
    seen: set[tuple[Any, ...]] = set()
    seen_bindings: set[int] = set()
    for item in items:
        bindings = item.field_bindings
        if id(bindings) in seen_bindings:
            continue
        seen_bindings.add(id(bindings))
        aliases_by_name: dict[str, list[str]] = {}
        for role, field_name in bindings.bindings:
            aliases_by_name.setdefault(field_name, []).append(role)
        for _object_id, descriptors in bindings.object_descriptors:
            for descriptor in descriptors:
                fact = StyleFieldFact(
                    descriptor.name,
                    descriptor.kind,
                    False,
                    None,
                    descriptor.cardinality,
                    descriptor.enum_values,
                    tuple(aliases_by_name.get(descriptor.name, ())),
                )
                key = (fact.name, fact.kind, fact.cardinality, fact.enum_values, fact.aliases)
                if key not in seen:
                    seen.add(key)
                    catalogue.append(fact)
    return tuple(catalogue)


def _comparison_category(item: Any | None) -> str | None:
    if item is None:
        return None
    value = display_finish_delta(item)
    if not isinstance(value, int) or isinstance(value, bool):
        return None
    return "behind" if value > 0 else "ahead" if value < 0 else "on-track"


def _occurrence(key: StyleOccurrenceKey, item: Any | None, *,
                column_source: str | tuple[tuple[str, str], ...] | None = None,
                mark_shape: str | None = None) -> StyleOccurrence:
    binding = semantic_binding(key.semantic_id)
    return StyleOccurrence(
        key,
        binding.purpose,
        binding.primitive_kind,
        tuple(item.roles) if item is not None else (),
        _comparison_category(item),
        column_source,
        field_facts_for_item(item) if item is not None else (),
        mark_shape,
    )


def _source_subject_index(projection: ReviewProjection) -> dict[tuple[str, str, str, str], Any]:
    """Index exact table-source identities once, including lane table aliases."""
    result: dict[tuple[str, str, str, str], Any] = {}

    def add(row_id: str, item: Any) -> None:
        key = (row_id, item.item_id or item.object_id, item.object_id, item.source_kind)
        previous = result.get(key)
        if previous is not None and previous != item:
            raise ValueError(f"E_STYLE_FACT_TYPE: ambiguous table source identity {key!r}")
        result[key] = item

    for row in projection.rows:
        for item in row.items:
            add(row.row_id, item)
    if projection.lane_membership is not None:
        for row in projection.lane_rows:
            for item in row.items:
                add(row.lane_id, item)
    if not projection.rows and not projection.rows_resolved:
        for item in projection.items:
            add(item.object_id, item)
    return result


def _cell_occurrences(projection: ReviewProjection,
                      content: SurfaceContentInput) -> tuple[StyleOccurrence, ...]:
    columns = {column.column_id: column for column in content.table_columns}
    source_items = _source_subject_index(projection)
    occurrences = []
    for cell in content.table_cells:
        key = cell.style_key
        if key is None:
            continue
        item = (None if key.source_kind == "view" else source_items.get(
            (key.row_id, key.member_id, key.subject_id, key.source_kind)))
        if key.source_kind != "view" and item is None:
            raise ValueError(f"E_STYLE_FACT_TYPE: table source identity did not resolve: {key!r}")
        column = columns.get(cell.column_id)
        source = column.column_source if column is not None else None
        occurrences.append(_occurrence(key, item, column_source=source))
    return tuple(occurrences)


def _text_occurrences(projection: ReviewProjection, content: SurfaceContentInput,
                      source_items: tuple[_SourceItem, ...]) -> tuple[StyleOccurrence, ...]:
    attached = dict(content.attached_labels)
    show_member_text = content.show_member_labels
    occurrences: list[StyleOccurrence] = []
    for source in source_items:
        item = source.item
        attached_text = (member_name_key(item, source.content_container_id) in attached
                         and item.attached_to is not None)
        if (getattr(item, "member_label_eligible", True)
                and (show_member_text or attached_text)
                and (source.occurrence_kind == "folded"
                     or getattr(item, "temporal_paint", True))):
            occurrences.append(_occurrence(source.key("memberLabel"), item))
            preferred_side = None
            presentation = getattr(item, "presentation", None)
            if (source.occurrence_kind != "folded" and isinstance(presentation, dict)
                    and isinstance(presentation.get("label"), dict)):
                preferred_side = presentation["label"].get("side")
            # Folded titles have their own end/start ladder; key-row titles
            # use the key-row ladder, even if ordinary labels admit inside.
            inside_possible = (
                source.occurrence_kind != "folded"
                and (content.label_side == "inside"
                     or "inside" in content.label_fallback
                     or preferred_side == "inside")
            )
            if not source.key_row and inside_possible:
                occurrences.append(_occurrence(
                    source.key(inside_member_label_semantic(item.source_kind)), item))

        if item.forecast is not None:
            if (source.occurrence_kind != "auto" and content.show_member_labels
                    and "finishDelta" in content.label_content):
                occurrences.append(_occurrence(source.key(finish_delta_semantic(item)), item))
            continue

        # A detached delta is a separate existing text occurrence when the
        # View does not append it to the member title. A delta appended to the
        # title is already covered by the single memberLabel occurrence above.
        if (item.finish_delta is not None
                and "finishDelta" not in content.label_content
                and projection.lane_membership is None
                and source.occurrence_kind != "folded"
                and (source.occurrence_kind != "auto" or item.source_kind == "combined")
                and getattr(item, "temporal_paint", True)):
            occurrences.append(_occurrence(source.key(finish_delta_semantic(item)), item))
    return tuple(occurrences)


def _selected_mark_facets(projection, content, source_items, *, gate_declared):
    """One source-facet selection for Style facts and semantic key candidates."""
    for source in source_items:
        emit_missing_actual = (
            source.occurrence_kind != "folded"
            and (source.occurrence_kind != "lane-source"
                 or not projection.comparison_facets
                 or "missingActual" in projection.comparison_facets)
        )
        selection = select_item_mark_facets(
            item=source.item, source_kind=source.source_kind, as_of=content.as_of,
            emit_missing_actual=emit_missing_actual, emit_diagnostics=False,
        )
        for facet in selection.facets:
            yield source, canonical_mark_semantic(
                facet.semantic_id, facet.shape, gate_declared=gate_declared), facet.shape


def surface_comparison_mark_semantics(projection: ReviewProjection, content: SurfaceContentInput,
                                      *, gate_declared: bool = False) -> frozenset[str]:
    """Potential comparison meanings without inspecting unrelated primary facets."""
    sources = tuple(source for source in _source_items(projection)
                    if source.source_kind in {"snapshot", "scenario"})
    return frozenset(semantic for _source, semantic, _shape in _selected_mark_facets(
        projection, content, sources, gate_declared=gate_declared))


def collect_surface_style_facts(
    projection: ReviewProjection,
    content: SurfaceContentInput,
    *,
    gate_declared: bool = False,
) -> SurfaceStyleFacts:
    """Collect mark, table-cell and admitted text facts without Layout geometry."""
    source_items = _source_items(projection)
    all_items = _all_source_items(projection)
    facts: list[StyleOccurrence] = []
    seen: dict[StyleOccurrenceKey, StyleOccurrence] = {}

    def add(occurrence: StyleOccurrence) -> None:
        previous = seen.get(occurrence.key)
        if previous is None:
            seen[occurrence.key] = occurrence
            facts.append(occurrence)
        elif previous != occurrence:
            # The exact source identity cannot denote two original facts.
            # Leave diagnosis at the common evaluator's duplicate-key gate.
            facts.append(occurrence)

    for source, semantic_id, shape in _selected_mark_facets(
            projection, content, source_items, gate_declared=gate_declared):
        add(_occurrence(source.key(semantic_id), source.item, mark_shape=shape))

    for occurrence in _cell_occurrences(projection, content):
        add(occurrence)
    for occurrence in _text_occurrences(projection, content, source_items):
        add(occurrence)

    return SurfaceStyleFacts(tuple(facts), _field_catalogue(all_items))
