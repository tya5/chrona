"""Project-neutral semantic annotation expansion; no measurement or geometry."""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from chrona.presentation.contracts.resources import (
    ContractError, FrozenDict, ViewInput, annotation_placement_for, freeze,
)
from chrona.presentation.model.projection import ReviewProjection


@dataclass(frozen=True)
class ExpandedAnnotation:
    value: FrozenDict
    anchor_source_ref: str


class AnnotationExpansionError(ContractError):
    """A new semantic expansion failure with its detector-owned source pointer."""


def _pointer(key: str) -> str:
    return key.replace("~", "~0").replace("/", "~1")


def expand_annotations(view: ViewInput, project_notes: Mapping[str, Any],
                       projection: ReviewProjection) -> tuple[ExpandedAnnotation, ...]:
    """Keep explicit intent, then select each unclaimed Project note at most once."""
    explicit = tuple(ExpandedAnnotation(value, f"/body/annotations/{index}/anchor")
                     for index, value in enumerate(view.annotations))
    if not view.annotation_bindings and view.annotation_placement is None:
        return explicit

    final = list(explicit)
    ids: dict[str, str] = {}

    def add_identity(annotation: ExpandedAnnotation) -> None:
        identifier = str(annotation.value["id"])
        if identifier in ids:
            raise AnnotationExpansionError("E_PRESENTATION_ANNOTATION_IDENTITY",
                                f"annotation_id={identifier!r}; firstSource={ids[identifier]}; "
                                f"secondSource={annotation.anchor_source_ref}",
                                annotation.anchor_source_ref)
        ids[identifier] = annotation.anchor_source_ref

    for annotation in explicit:
        add_identity(annotation)
    consumed = {str(item.value["projectAnnotation"]) for item in explicit
                if "projectAnnotation" in item.value}
    current_items = (*projection.items,
                     *(item for folded in projection.folded_points for item in folded.all_items))
    selected = {item.object_id: item.source_type for item in current_items
                if item.source_kind in {"primary", "combined"}}
    keys = tuple(sorted(project_notes))
    for binding in view.annotation_bindings:
        for key in keys:
            if key in consumed:
                continue
            note = project_notes[key]
            if not isinstance(note, Mapping) or note.get("kind") != binding["kind"]:
                continue
            anchor = note.get("anchor")
            object_id = anchor.get("object") if isinstance(anchor, Mapping) else None
            shape = selected.get(object_id)
            if shape is None or binding["temporalKind"] not in {"any", shape}:
                continue
            source_ref = f"/annotations/{_pointer(str(key))}/anchor"
            purpose = str(binding["purpose"])
            try:
                policy = annotation_placement_for(view.annotation_placement, purpose,
                                                  f"/body/annotationPlacement/{_pointer(purpose)}")
            except ContractError as error:
                raise AnnotationExpansionError(error.diagnostic_id, error.detail, error.source_ref) from error
            value = freeze({"id": f"{key}-{purpose}", "purpose": purpose,
                            "anchor": {"kind": "object", "id": object_id,
                                       "facet": binding["facet"], "endpoint": binding["endpoint"]},
                            "projectAnnotation": key, **policy})
            annotation = ExpandedAnnotation(value, source_ref)
            add_identity(annotation)
            final.append(annotation)
            consumed.add(str(key))
    return tuple(final)
