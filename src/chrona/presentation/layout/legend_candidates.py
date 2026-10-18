"""Prepare conservative, realized-paint legend candidates before measurement."""
from __future__ import annotations

from dataclasses import replace

from chrona.presentation.layout.legend_ink import source_actual_keys, progress_ink_key
from chrona.presentation.model.legend_paint import RealizedLegendKey
from chrona.presentation.model.paint_capabilities import PaintWitnessCapabilities
from chrona.presentation.model.surface_content import SurfaceContentInput, SurfaceLegendEntry
from chrona.presentation.model.theme_tokens import ThemeTokenView


_VARIANCE_ORDER = ("ahead", "on-track", "behind")
_VARIANCE_LABELS = {
    "ahead": ("actual-ahead", "Ahead"),
    "on-track": ("actual-on-track", "On track"),
    "behind": ("actual-behind", "Behind"),
}


def _wording(content: SurfaceContentInput) -> dict[str, str]:
    return dict(content.legend_wording)


def _ordered_classes(keys: tuple[RealizedLegendKey, ...]) -> tuple[str, ...]:
    present = {category for key in keys for category in key.variance_classes}
    return tuple(category for category in _VARIANCE_ORDER if category in present)


def coalesce_actual_keys(keys: tuple[RealizedLegendKey, ...]) -> tuple[RealizedLegendKey, ...]:
    """Merge equal actual ink in first-seen order while retaining all witnesses."""
    grouped: dict[tuple[object, ...], list[RealizedLegendKey]] = {}
    for key in keys:
        grouped.setdefault(key.identity, []).append(key)
    result = []
    for group in grouped.values():
        first = group[0]
        occurrences = tuple(dict.fromkeys(occurrence for key in group for occurrence in key.occurrences))
        classes = _ordered_classes(tuple(group))
        glyph = first.glyph
        if glyph is not None:
            glyph = replace(glyph, footprint=tuple(
                max(key.glyph.footprint[axis] for key in group) for axis in (0, 1)))
        result.append(replace(first, occurrences=occurrences, variance_classes=classes, glyph=glyph))
    return tuple(result)


def actual_key_label(base: str, key: RealizedLegendKey, *, multiple: bool,
                     wording: dict[str, str]) -> str:
    if not multiple:
        return base
    fragments = tuple(wording.get(_VARIANCE_LABELS[category][0], _VARIANCE_LABELS[category][1])
                      for category in _ordered_classes((key,)))
    return f"{base} — {' / '.join(fragments)}" if fragments else base


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
    has_actual_candidate = any(entry.role == "actual" for entry in entries)
    actual_keys = (coalesce_actual_keys(source_actual_keys(
        content, tokens, mark_block_size=mark_block_size,
        paint_capabilities=paint_capabilities)) if has_actual_candidate else ())
    prepared: list[SurfaceLegendEntry] = []
    actual_written = False
    explicit_progress = next((entry for entry in entries if entry.role == "progressFill"), None)
    progress_entry = None
    if content.legend_progress_possible:
        progress_key = progress_ink_key(tokens, paint_capabilities)
        progress_entry = replace(
            explicit_progress,
            label=wording.get("progressFill", explicit_progress.label),
            source_ref=None,
            realized_key=progress_key,
        ) if explicit_progress is not None else SurfaceLegendEntry(
            "progressFill", wording.get("progressFill", "Progress"), realized_key=progress_key)
    progress_written = False

    for entry in entries:
        if entry.role == "progressFill":
            if progress_entry is not None and not progress_written:
                prepared.append(progress_entry)
                progress_written = True
            continue
        if entry.role != "actual":
            prepared.append(entry)
            continue
        if not actual_written:
            base_label = wording.get("actual", entry.label)
            if actual_keys:
                prepared.extend(replace(
                    entry,
                    label=actual_key_label(base_label, key, multiple=len(actual_keys) > 1, wording=wording),
                    source_ref=None,
                    realized_key=replace(key, base_label=base_label),
                ) for key in actual_keys)
            actual_written = True

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
