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


def _brief(value: object) -> str:
    """Describe one invalid declaration operand without dumping a whole Theme or View."""
    if isinstance(value, str):
        text = repr(value[:80])
        return text if len(value) <= 80 else text[:-1] + "…'"
    if value is None or isinstance(value, (bool, int, float)):
        return repr(value)
    if isinstance(value, Mapping):
        return "mapping"
    if isinstance(value, (list, tuple)):
        return f"{type(value).__name__} of length {len(value)}"
    return type(value).__name__


def _invalid_mapping(detail: str) -> ColorScaleError:
    return ColorScaleError(f"E_PRESENTATION_SCALE_MAPPING: {detail}")


def _key_summary(mapping: Mapping[object, object], domain: tuple[str, ...]) -> str:
    missing = [_brief(value) for value in domain if value not in mapping]
    extra = [_brief(key) for key in mapping if key not in domain]
    if len(missing) > 8:
        missing = missing[:8] + [f"… (+{len(missing) - 8} more)"]
    if len(extra) > 8:
        extra = extra[:8] + [f"… (+{len(extra) - 8} more)"]
    return f"missing keys={missing!r}, extra keys={extra!r}"


@dataclass(frozen=True)
class ResolvedColorScale:
    """One immutable, explicit mapping for an eligible mark role."""

    scale_id: str
    target_role: str
    source_field: str
    domain: tuple[str, ...]
    colors: tuple[tuple[str, str], ...]
    collisions: tuple[ScaleCollision, ...] = ()
    # A firstAppearance domain admits only observed values; an item without
    # the field keeps its role's own paint instead of failing.
    derived: bool = False

    def covers(self, fields: Mapping[str, object] | None) -> bool:
        """Whether this scale paints an item: always for a closed domain."""
        return not self.derived or (isinstance(fields, Mapping) and fields.get(self.source_field) is not None)

    def color_for(self, object_id: str, fields: Mapping[str, object] | None) -> str:
        """Resolve one selected object's declared scalar value without fallback."""
        value = fields.get(self.source_field) if isinstance(fields, Mapping) else None
        if not isinstance(value, str) or value not in self.domain:
            raise ColorScaleError(f"E_PRESENTATION_SCALE_VALUE:{object_id}:{self.source_field}")
        return dict(self.colors)[value]


def resolve_color_scale(encoding: Mapping[str, object] | None,
                        scales: Mapping[str, object] | None,
                        categories: Mapping[str, object] | None,
                        *, color_vision: tuple[str, ...] = (),
                        observed: tuple[str, ...] = ()) -> ResolvedColorScale | None:
    """Resolve one View encoding against exact Theme and Scheme declarations.

    Domain values whose colours a reader cannot separate, under normal vision
    or a vision the Scheme claims, are returned as non-fatal collisions.
    A ``firstAppearance`` domain is the distinct ``observed`` source values in
    projection order; a Theme ``palette`` assigns them slots cyclically.
    """
    if encoding is None:
        return None
    if not isinstance(encoding, Mapping) or not isinstance(scales, Mapping) or not isinstance(categories, Mapping):
        invalid = [(name, value) for name, value in (
            ("encoding", encoding), ("scales", scales), ("categories", categories),
        ) if not isinstance(value, Mapping)]
        detail = ", ".join(f"{name}={_brief(value)} (type {type(value).__name__}), expected a mapping"
                            for name, value in invalid)
        raise _invalid_mapping(detail)
    scale_id, target = encoding.get("scale"), encoding.get("target")
    source = encoding.get("source")
    domain = encoding.get("domain")
    derived = domain == "firstAppearance"
    if derived:
        domain = tuple(dict.fromkeys(observed))
        if not domain:
            return None
    if not isinstance(scale_id, str):
        raise _invalid_mapping(f"encoding.scale={_brief(scale_id)}; expected a string scale id")
    if not isinstance(target, str):
        raise _invalid_mapping(f"encoding.target={_brief(target)}; expected a string target role")
    if not isinstance(source, Mapping):
        raise _invalid_mapping(f"encoding.source={_brief(source)}; expected a mapping with a string field")
    source_field = source.get("field")
    if not isinstance(source_field, str):
        raise _invalid_mapping(f"encoding.source.field={_brief(source_field)}; expected a string field name")
    if not isinstance(domain, (list, tuple)) or not domain:
        raise _invalid_mapping(f"encoding.domain={_brief(domain)}; expected a nonempty sequence of unique strings")
    invalid_index = next((index for index, value in enumerate(domain) if not isinstance(value, str)), None)
    if invalid_index is not None:
        raise _invalid_mapping(f"encoding.domain[{invalid_index}]={_brief(domain[invalid_index])}; every domain value must be a string")
    seen: set[str] = set()
    for index, value in enumerate(domain):
        if value in seen:
            raise _invalid_mapping(f"encoding.domain[{index}]={_brief(value)} duplicates an earlier domain value")
        seen.add(value)
    declared = scales.get(scale_id)
    palette = declared.get("palette") if isinstance(declared, Mapping) else None
    slots = ({value: palette[index % len(palette)] for index, value in enumerate(domain)}
             if isinstance(palette, (list, tuple)) and palette else
             declared.get("slots") if isinstance(declared, Mapping) else None)
    if not isinstance(slots, Mapping):
        raise _invalid_mapping(f"Theme scale {_brief(scale_id)} has slots={_brief(slots)}; expected a slots mapping or nonempty palette")
    if set(slots) != set(domain):
        raise _invalid_mapping(f"Theme scale {_brief(scale_id)} does not exactly cover the {len(domain)} encoding.domain values; {_key_summary(slots, tuple(domain))}")
    colors: list[tuple[str, str]] = []
    for value in domain:
        slot = slots[value]
        if not isinstance(slot, str):
            raise _invalid_mapping(f"Theme scale {_brief(scale_id)} maps domain value {_brief(value)} to slot={_brief(slot)}; expected a string Scheme category")
        color = categories.get(slot)
        if not isinstance(color, str):
            if slot not in categories:
                raise _invalid_mapping(f"Theme scale {_brief(scale_id)} maps domain value {_brief(value)} to missing Scheme category {_brief(slot)}")
            raise _invalid_mapping(f"Scheme category {_brief(slot)} has color={_brief(color)}; expected a string color")
        colors.append((value, color))
    return ResolvedColorScale(scale_id, target, source["field"], tuple(domain), tuple(colors),
                              scale_collisions(scale_id, tuple(colors), color_vision), derived)
