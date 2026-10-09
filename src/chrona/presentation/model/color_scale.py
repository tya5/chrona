"""Typed, total field-to-colour scale resolution.

This module is deliberately independent of Layout and renderer adapters.  A
closure supplies a declared scale and projection supplies selected object
fields; callers receive concrete colours or a stable rejection.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field

from chrona.presentation.model.color_separability import ScaleCollision, scale_collisions


class ColorScaleError(ValueError):
    """A closed scale cannot resolve one declared presentation input."""

    def __init__(self, code: str, detail: str, source_ref: str = "/") -> None:
        self.code = code
        self.detail = detail
        self.source_ref = source_ref
        super().__init__(f"{code}: {detail}")


def _brief(value: object) -> str:
    """Describe one invalid declaration operand without dumping a whole Theme or View."""
    if isinstance(value, str):
        text = repr(value[:80])
        return text if len(value) <= 80 else text[:-1] + "…'"
    if isinstance(value, int) and not isinstance(value, bool) and value.bit_length() > 320:
        return f"<int bits={value.bit_length()}>"
    if value is None or isinstance(value, (bool, int, float)):
        return repr(value)
    if isinstance(value, Mapping):
        return "mapping"
    if isinstance(value, (list, tuple)):
        return f"{type(value).__name__} of length {len(value)}"
    return type(value).__name__


def _invalid_mapping(detail: str, source_ref: str) -> ColorScaleError:
    return ColorScaleError("E_PRESENTATION_SCALE_MAPPING", detail, source_ref)


def _pointer_token(value: str) -> str:
    return value.replace("~", "~0").replace("/", "~1")


def _key_summary(mapping: Mapping[object, object], domain: tuple[str, ...]) -> str:
    missing = [_brief(value) for value in domain if value not in mapping]
    extra = [_brief(key) for key in mapping if key not in domain]
    if len(missing) > 8:
        missing = missing[:8] + [f"… (+{len(missing) - 8} more)"]
    if len(extra) > 8:
        extra = extra[:8] + [f"… (+{len(extra) - 8} more)"]
    return f"missing keys={missing!r}, extra keys={extra!r}"


def _domain_summary(domain: tuple[str, ...]) -> str:
    sample = tuple(_brief(value) for value in domain[:8])
    suffix = f", … (+{len(domain) - 8} more)" if len(domain) > 8 else ""
    return f"{len(domain)} values ({sample!r}{suffix})"


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
    # Runtime provenance only: the View field that selected this scale is not
    # paint identity and must not affect equality, hashing, or repr.
    encoding_source_ref: str = field(default="/body/colorEncoding", compare=False, repr=False)

    def covers(self, fields: Mapping[str, object] | None) -> bool:
        """Whether this scale paints an item: always for a closed domain."""
        return not self.derived or (isinstance(fields, Mapping) and fields.get(self.source_field) is not None)

    def color_for(self, object_id: str, fields: Mapping[str, object] | None) -> str:
        """Resolve one selected object's declared scalar value without fallback."""
        value = fields.get(self.source_field) if isinstance(fields, Mapping) else None
        if not isinstance(value, str) or value not in self.domain:
            raise ColorScaleError("E_PRESENTATION_SCALE_VALUE",
                                  f"object={_brief(object_id)}, field={_brief(self.source_field)}, value={_brief(value)}; expected domain {_domain_summary(self.domain)}",
                                  self.encoding_source_ref)
        return dict(self.colors)[value]


def resolve_color_scale(encoding: Mapping[str, object] | None,
                        scales: Mapping[str, object] | None,
                        categories: Mapping[str, object] | None,
                        *, source_ref: str = "/body/colorEncoding",
                        color_vision: tuple[str, ...] = (),
                        observed: tuple[str, ...] = ()) -> ResolvedColorScale | None:
    """Resolve one View encoding against exact Theme and Scheme declarations.

    Domain values whose colours a reader cannot separate, under normal vision
    or a vision the Scheme claims, are returned as non-fatal collisions.
    A ``firstAppearance`` domain is the distinct ``observed`` source values in
    projection order; a Theme ``palette`` assigns them slots cyclically.
    """
    if encoding is None:
        return None
    if not isinstance(encoding, Mapping):
        invalid = [("encoding", encoding)]
        detail = ", ".join(f"{name}={_brief(value)} (type {type(value).__name__}), expected a mapping"
                            for name, value in invalid)
        raise _invalid_mapping(detail, source_ref)
    if not isinstance(scales, Mapping):
        raise _invalid_mapping(f"Theme colorScales={_brief(scales)} (type {type(scales).__name__}); expected a mapping",
                               "/body/colorScales")
    if not isinstance(categories, Mapping):
        raise ColorScaleError("E_SCHEME_SCHEMA",
                              f"categories={_brief(categories)} (type {type(categories).__name__}); expected a mapping",
                              "/body/categories")
    scale_id, target = encoding.get("scale"), encoding.get("target")
    source = encoding.get("source")
    domain = encoding.get("domain")
    derived = domain == "firstAppearance"
    if derived:
        domain = tuple(dict.fromkeys(observed))
        if not domain:
            return None
    if not isinstance(scale_id, str):
        raise _invalid_mapping(f"encoding.scale={_brief(scale_id)}; expected a string scale id", source_ref)
    if not isinstance(target, str):
        raise _invalid_mapping(f"encoding.target={_brief(target)}; expected a string target role", source_ref)
    if not isinstance(source, Mapping):
        raise _invalid_mapping(f"encoding.source={_brief(source)}; expected a mapping with a string field", source_ref)
    source_field = source.get("field")
    if not isinstance(source_field, str):
        raise _invalid_mapping(f"encoding.source.field={_brief(source_field)}; expected a string field name", source_ref)
    if not isinstance(domain, (list, tuple)) or not domain:
        raise _invalid_mapping(f"encoding.domain={_brief(domain)}; expected a nonempty sequence of unique strings", source_ref)
    invalid_index = next((index for index, value in enumerate(domain) if not isinstance(value, str)), None)
    if invalid_index is not None:
        raise _invalid_mapping(f"encoding.domain[{invalid_index}]={_brief(domain[invalid_index])}; every domain value must be a string", source_ref)
    seen: set[str] = set()
    for index, value in enumerate(domain):
        if value in seen:
            raise _invalid_mapping(f"encoding.domain[{index}]={_brief(value)} duplicates an earlier domain value", source_ref)
        seen.add(value)
    declared = scales.get(scale_id)
    theme_pointer = f"/body/colorScales/{_pointer_token(scale_id)}/slots"
    palette = declared.get("palette") if isinstance(declared, Mapping) else None
    slots = ({value: palette[index % len(palette)] for index, value in enumerate(domain)}
             if isinstance(palette, (list, tuple)) and palette else
             declared.get("slots") if isinstance(declared, Mapping) else None)
    if not isinstance(slots, Mapping):
        raise _invalid_mapping(f"Theme scale {_brief(scale_id)} has slots={_brief(slots)}; expected a slots mapping or nonempty palette", theme_pointer)
    if set(slots) != set(domain):
        raise _invalid_mapping(f"Theme scale {_brief(scale_id)} does not exactly cover the {len(domain)} encoding.domain values; {_key_summary(slots, tuple(domain))}", theme_pointer)
    colors: list[tuple[str, str]] = []
    for value in domain:
        slot = slots[value]
        if not isinstance(slot, str):
            raise _invalid_mapping(f"Theme scale {_brief(scale_id)} maps domain value {_brief(value)} to slot={_brief(slot)}; expected a string Scheme category", theme_pointer)
        color = categories.get(slot)
        if not isinstance(color, str):
            if slot not in categories:
                raise _invalid_mapping(f"Theme scale {_brief(scale_id)} maps domain value {_brief(value)} to missing Scheme category {_brief(slot)}", theme_pointer)
            raise _invalid_mapping(f"Scheme category {_brief(slot)} has color={_brief(color)}; expected a string color",
                                   f"/body/categories/{_pointer_token(slot)}")
        colors.append((value, color))
    return ResolvedColorScale(scale_id, target, source["field"], tuple(domain), tuple(colors),
                              scale_collisions(scale_id, tuple(colors), color_vision), derived,
                              source_ref)
