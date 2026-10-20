"""Prepare conservative, realized-paint legend candidates before measurement."""
from __future__ import annotations

from dataclasses import replace
from itertools import combinations

from chrona.presentation.layout.legend_ink import source_actual_keys, source_point_keys, progress_ink_key
from chrona.presentation.model.legend_paint import RealizedLegendKey
from chrona.presentation.model.paint_capabilities import PaintWitnessCapabilities
from chrona.presentation.model.surface_content import SurfaceContentInput, SurfaceLegendEntry
from chrona.presentation.model.theme_tokens import ThemeTokenView
from chrona.presentation.model.wording_tables import WordingResolver


_VARIANCE_ORDER = ("ahead", "on-track", "behind")
_VARIANCE_ROLES = {"ahead": "actual-ahead", "on-track": "actual-on-track", "behind": "actual-behind"}


def _wording(content: SurfaceContentInput) -> dict[str, str]:
    """Authored `wording.legend` overrides over the locale defaults the content builder carried (#1724)."""
    return {**dict(content.legend_defaults), **dict(content.legend_wording)}


def _ordered_classes(keys: tuple[RealizedLegendKey, ...]) -> tuple[str, ...]:
    present = {category for key in keys for category in key.variance_classes}
    return tuple(category for category in _VARIANCE_ORDER if category in present)


def _coalesce_keys(keys: tuple[RealizedLegendKey, ...]) -> tuple[RealizedLegendKey, ...]:
    """Merge equal meaning/ink in first-seen order, retaining all witnesses."""
    grouped: dict[tuple[object, ...], list[RealizedLegendKey]] = {}
    for key in keys:
        grouped.setdefault(key.grouping_identity, []).append(key)
    result = []
    for group in grouped.values():
        first = group[0]
        occurrences = tuple(dict.fromkeys(occurrence for key in group for occurrence in key.occurrences))
        classes = _ordered_classes(tuple(group))
        glyph = first.glyph
        if glyph is not None:
            glyphs = tuple(key.glyph for key in group if key.glyph is not None)
            glyph = replace(glyph, footprint=tuple(
                max(item.footprint[axis] for item in glyphs) for axis in (0, 1)))
        covered = {state for key in group for state in key.point_states}
        states = tuple(state for state in ("planned", "actual", "forecast") if state in covered)
        result.append(replace(first, occurrences=occurrences, variance_classes=classes, glyph=glyph,
                              covered_point_states=states))
    return tuple(result)


def coalesce_actual_keys(keys: tuple[RealizedLegendKey, ...]) -> tuple[RealizedLegendKey, ...]:
    return _coalesce_keys(keys)


def coalesce_point_keys(keys: tuple[RealizedLegendKey, ...]) -> tuple[RealizedLegendKey, ...]:
    ordered = _coalesce_keys(keys)
    return tuple(key for state in ("planned", "actual", "forecast")
                 for key in ordered if key.point_states[0] == state)


def point_key_label(base: str, key: RealizedLegendKey, *, multiple: bool,
                    wording: dict[str, str]) -> str:
    if key.family in {"planned", "actual", "forecast"}:
        qualifier = "milestone"
    elif multiple:
        qualifiers = ("planned-plain" if state == "planned" else state for state in key.point_states)
        return base + " · " + " / ".join(
            wording.get(qualifier) or WordingResolver().legend_text(qualifier) for qualifier in qualifiers)
    else:
        return base
    return base + " · " + (wording.get(qualifier) or WordingResolver().legend_text(qualifier))


def _point_label_variants(base, key, *, multiple, wording):
    variants = [point_key_label(base, key, multiple=False, wording=wording)]
    if multiple:
        for count in range(1, len(key.point_states) + 1):
            for states in combinations(key.point_states, count):
                variants.append(point_key_label(base, replace(key, covered_point_states=states),
                                                multiple=True, wording=wording))
    return tuple(dict.fromkeys(variants))


def actual_key_label(base: str, key: RealizedLegendKey, *, multiple: bool,
                     wording: dict[str, str]) -> str:
    if not multiple:
        return base
    classes = _ordered_classes((key,))
    if len(classes) != 1:
        return base
    category = classes[0]
    role = _VARIANCE_ROLES[category]
    return wording.get(role) or WordingResolver().legend_text(role)


def prepare_realized_legend_candidates(
    content: SurfaceContentInput,
    tokens: ThemeTokenView,
    *,
    mark_block_size: float,
    paint_capabilities: PaintWitnessCapabilities,
) -> SurfaceContentInput:
    """Reserve every potential realized Actual and positive Progress key before sizing.

    This does not inspect completed Layout placements. The later final-visibility
    pass may remove candidates, but it must not discover a key that was not
    reserved here.
    """
    entries = content.legend_entries
    wording = _wording(content)
    legend_overrides = dict(content.legend_wording)
    has_actual_candidate = any(entry.role == "actual" for entry in entries)
    actual_keys = (coalesce_actual_keys(source_actual_keys(
        content, tokens, mark_block_size=mark_block_size,
        paint_capabilities=paint_capabilities)) if has_actual_candidate else ())
    point_keys = coalesce_point_keys(source_point_keys(
        content, tokens, mark_block_size=mark_block_size, paint_capabilities=paint_capabilities))
    point_owners = {key.family for key in point_keys}
    point_written: set[str] = set()
    prepared: list[SurfaceLegendEntry] = []
    actual_written = False
    explicit_progress = next((entry for entry in entries if entry.role == "progressFill"), None)
    progress_entry = None
    if content.legend_progress_possible:
        progress_key = progress_ink_key(tokens, paint_capabilities)
        progress_entry = replace(
            explicit_progress,
            label=legend_overrides.get("progressFill", explicit_progress.label),
            source_ref=None,
            realized_key=progress_key,
        ) if explicit_progress is not None else SurfaceLegendEntry(
            "progressFill", wording.get("progressFill") or WordingResolver().legend_text("progressFill"), realized_key=progress_key)
    progress_written = False

    for entry in entries:
        if entry.role == "progressFill":
            if progress_entry is not None and not progress_written:
                prepared.append(progress_entry)
                progress_written = True
            continue
        eligible_owner = (entry.source_ref is None and entry.style_scope is None
                          and entry.view_scale_id is None and entry.encoding_scale_id is None
                          and not entry.encoding_value_is_wording and not entry.role.startswith("scale:"))
        owned = tuple(key for key in point_keys if key.family == entry.role) if eligible_owner else ()
        if entry.role != "actual" and (not eligible_owner or entry.role not in point_owners
                                       or entry.role in {"planned", "forecast"}):
            prepared.append(entry)
        if entry.role == "actual" and not actual_written:
            base_label = legend_overrides.get("actual", entry.label)
            if actual_keys:
                prepared.extend(replace(
                    entry,
                    label=actual_key_label(base_label, key, multiple=len(actual_keys) > 1, wording=wording),
                    source_ref=None,
                    realized_key=replace(key, base_label=base_label),
                ) for key in actual_keys)
            actual_written = True
        if owned and entry.role not in point_written:
            base_label = legend_overrides.get(entry.role, entry.label)
            prepared.extend(replace(entry,
                label=point_key_label(base_label, key, multiple=len(owned) > 1, wording=wording),
                label_variants=_point_label_variants(base_label, key, multiple=len(owned) > 1, wording=wording),
                source_ref=None, realized_key=replace(key, base_label=base_label)) for key in owned)
            point_written.add(entry.role)

    if progress_entry is not None and explicit_progress is None:
        actual_indexes = [i for i, entry in enumerate(prepared) if entry.role == "actual"]
        if actual_indexes:
            insert_at = actual_indexes[-1] + 1
        else:
            fallback_indexes = [i for i, entry in enumerate(prepared) if entry.role in {"planned", "forecast"}]
            insert_at = fallback_indexes[-1] + 1 if fallback_indexes else len(prepared)
        prepared.insert(insert_at, progress_entry)

    # Keep an explicitly authored Actual candidate only when it has at least
    # one possible ink witness; actual keys are never synthesized otherwise.
    return replace(content, legend_entries=tuple(prepared))
