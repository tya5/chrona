"""Typed, total field-to-colour scale resolution.

This module is deliberately independent of Layout and renderer adapters.  A
closure supplies a declared scale and projection supplies selected object
fields; callers receive concrete colours or a stable rejection.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from chrona.presentation.model.color_separability import ScaleCollision, scale_collisions


class ColorScaleError(ValueError):
    """A closed scale cannot resolve one declared presentation input."""


@dataclass(frozen=True)
class ResolvedColorScale:
    """One immutable, explicit mapping for an eligible mark role."""

    scale_id: str
    target_role: str
    source_field: str
    domain: tuple[str, ...]
    colors: tuple[tuple[str, str], ...]
    collisions: tuple[ScaleCollision, ...] = ()

    def color_for(self, object_id: str, fields: Mapping[str, object] | None) -> str:
        """Resolve one selected object's declared scalar value without fallback."""
        value = fields.get(self.source_field) if isinstance(fields, Mapping) else None
        if not isinstance(value, str) or value not in self.domain:
            raise ColorScaleError(f"E_PRESENTATION_SCALE_VALUE:{object_id}:{self.source_field}")
        return dict(self.colors)[value]


def resolve_color_scale(encoding: Mapping[str, object] | None,
                        scales: Mapping[str, object] | None,
                        categories: Mapping[str, object] | None,
                        *, color_vision: tuple[str, ...] = ()) -> ResolvedColorScale | None:
    """Resolve one View encoding against exact Theme and Scheme declarations.

    Domain values whose colours a reader cannot separate, under normal vision
    or a vision the Scheme claims, are returned as non-fatal collisions.
    """
    if encoding is None:
        return None
    if not isinstance(encoding, Mapping) or not isinstance(scales, Mapping) or not isinstance(categories, Mapping):
        raise ColorScaleError("E_PRESENTATION_SCALE_MAPPING")
    scale_id, target = encoding.get("scale"), encoding.get("target")
    source = encoding.get("source")
    domain = encoding.get("domain")
    if (not isinstance(scale_id, str) or not isinstance(target, str)
            or not isinstance(source, Mapping) or not isinstance(source.get("field"), str)
            or not isinstance(domain, (list, tuple)) or not domain
            or any(not isinstance(value, str) for value in domain) or len(set(domain)) != len(domain)):
        raise ColorScaleError("E_PRESENTATION_SCALE_MAPPING")
    declared = scales.get(scale_id)
    slots = declared.get("slots") if isinstance(declared, Mapping) else None
    if not isinstance(slots, Mapping) or set(slots) != set(domain):
        raise ColorScaleError("E_PRESENTATION_SCALE_MAPPING")
    colors: list[tuple[str, str]] = []
    for value in domain:
        slot = slots[value]
        color = categories.get(slot) if isinstance(slot, str) else None
        if not isinstance(color, str):
            raise ColorScaleError("E_PRESENTATION_SCALE_MAPPING")
        colors.append((value, color))
    return ResolvedColorScale(scale_id, target, source["field"], tuple(domain), tuple(colors),
                              scale_collisions(scale_id, tuple(colors), color_vision))
