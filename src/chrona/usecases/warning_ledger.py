"""One successful-render warning inventory for Scene and CLI projection."""
from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Any, Iterable, Mapping

from chrona.usecases.diagnostic_messages import describe_warning, warning_message


@dataclass(frozen=True)
class RenderWarning:
    identity: str
    payload: Mapping[str, Any]


def _record(code: str, identity_fields: Mapping[str, Any], **fields: Any) -> RenderWarning:
    identity = code + ":" + json.dumps(identity_fields, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return RenderWarning(identity, {"code": code, "severity": "warning", "diagnostic": identity, **fields})


def _described(record: RenderWarning) -> RenderWarning:
    """The record with the ``message`` every render warning carries (#782): its cause and its subject."""
    return RenderWarning(record.identity, {**record.payload, "message": warning_message(describe_warning(record.payload))})


def collect_render_warnings(
    *, surface_diagnostics: Iterable[str], tabular_warnings: Iterable[Any],
    glyph_warnings: Iterable[Any], fit_warnings: Iterable[Any],
    perceptibility_warnings: Iterable[Any], scale_collisions: Iterable[Any],
    attachment_warnings: Iterable[Any], deadline_warnings: Iterable[Any] = (),
    contrast_warnings: Iterable[Any] = (),
) -> tuple[RenderWarning, ...]:
    """Keep warning multiplicity and stable source identities across transports."""
    records = []
    for diagnostic in surface_diagnostics:
        if diagnostic.startswith("W_"):
            records.append(RenderWarning(diagnostic, {
                "code": diagnostic.split(":", 1)[0], "severity": "warning", "diagnostic": diagnostic,
            }))
    for item in tabular_warnings:
        records.append(_record("W_FONT_TABULAR_UNAVAILABLE",
                               {"role": item.role, "family": item.family, "weight": item.weight},
                               role=item.role, family=item.family, weight=item.weight,
                               requestedSpacing=item.requested_spacing,
                               effectiveSpacing=item.effective_spacing))
    for item in glyph_warnings:
        records.append(_record("W_FONT_GLYPH_SUBSTITUTED",
                               {"requestedFamily": item.requested_family, "fallbackFamily": item.fallback_family,
                                "weight": item.weight, "codepoint": item.codepoint, "text": item.text},
                               requestedFamily=item.requested_family, fallbackFamily=item.fallback_family,
                               weight=item.weight, codepoint=f"U+{item.codepoint:04X}", text=item.text,
                               **({"drawn": item.drawn} if item.drawn is not None else {})))
    for item in fit_warnings:
        records.append(_record(item.code, {"placementId": item.placement_id, "sourceRef": item.source_ref,
                                           "failureKind": item.failure_kind},
                               placementId=item.placement_id, sourceRef=item.source_ref,
                               failureKind=item.failure_kind, behaviour=item.behaviour,
                               requiredInline=item.required_inline, requiredBlock=item.required_block,
                               availableInline=item.available_inline, availableBlock=item.available_block))
    for item in perceptibility_warnings:
        records.append(_record(item.code, {"scenePath": item.scene_path,
                                           "primitiveIds": list(item.primitive_ids)},
                               findingCode=item.finding_code, scenePath=item.scene_path,
                               primitiveIds=list(item.primitive_ids), measuredFacts=dict(item.measured_facts),
                               **({"slotId": item.slot_id} if item.slot_id is not None else {}),
                               **({"disposition": item.disposition} if item.disposition is not None else {})))
    for item in contrast_warnings:
        # A decoration below its floor (#995): a typed warning that fails nothing unless the Theme asks it to.
        records.append(_record(item.code, {"scenePath": item.scene_path, "primitiveIds": list(item.primitive_ids)},
                               findingCode=item.finding_code, scenePath=item.scene_path,
                               primitiveIds=list(item.primitive_ids), measuredFacts=dict(item.measured_facts),
                               **({"disposition": item.disposition} if item.disposition is not None else {})))
    for item in scale_collisions:
        records.append(RenderWarning(item.scene_diagnostic(), {
            "code": item.code, "severity": "warning", "diagnostic": item.scene_diagnostic(),
            "scaleId": item.scale_id, "values": [item.first, item.second], "vision": item.vision,
            "deltaE": item.delta_e,
        }))
    for item in attachment_warnings:
        records.append(_record(item.code, {"sourceRef": item.object_id, "host": item.host_id},
                               sourceRef=item.object_id, host=item.host_id))
    for item in deadline_warnings:
        # A family that says what is wrong carries its own message; the catalogue does not replace it.
        records.append(_record(item.id, {"sourceRef": item.path}, sourceRef=item.path, message=item.message,
                               **item.details))
    return tuple(_described(record) for record in records)
