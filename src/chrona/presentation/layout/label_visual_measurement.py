"""Shared Layout measurement for text runs with View-selected icon visuals."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from chrona.presentation.layout.model import LayoutError, geometry_sum
from chrona.presentation.layout.text import measure_text_width, metric_for_role


@dataclass(frozen=True)
class LabelVisualRunMeasurement:
    """Natural text and visual advances, before any candidate is placed.

    ``visuals`` retains the resolved View request and normalized icon asset
    beside its exact Layout-computed width and gap. Placement remains the
    caller's responsibility.
    """

    text_width: float
    text_block_size: float
    leading_advance: float
    trailing_advance: float
    visuals: tuple[tuple[Any, Any, float, float], ...]

    @property
    def required_inline_size(self) -> float:
        return self.leading_advance + self.text_width + self.trailing_advance


def measure_label_visual_run(placement_id: str, content: str, typography_role: str, *,
                             visual_requests: tuple[Any, ...], icon_assets: dict[str, Any],
                             theme_tokens: Any, font_metrics: Any) -> LabelVisualRunMeasurement:
    """Measure one complete text run and its resolved leading/trailing icons.

    The caller supplies the already-normalized text (including any selected
    delta) and the final projection-instance placement identity. Both ordinary
    text composition and future candidate solvers can use this same measurement
    without teaching their allocator about Theme, icons, or View selectors.
    """
    treatment = theme_tokens.text_treatment(typography_role)
    metric = metric_for_role(theme_tokens, typography_role, font_metrics)
    visuals = resolve_label_visual_advances(
        placement_id, typography_role, visual_requests=visual_requests,
        icon_assets=icon_assets, theme_tokens=theme_tokens,
    )
    text_width = measure_text_width(
        content, font_size=float(treatment.font_size), font_metrics=metric,
        letter_spacing=float(treatment.letter_spacing),
        text_transform=treatment.transform, numeric_spacing=treatment.numeric_spacing,
    )
    leading = geometry_sum(width + gap for visual, icon, width, gap in visuals if visual.side == "leading")
    trailing = geometry_sum(width + gap for visual, icon, width, gap in visuals if visual.side == "trailing")
    return LabelVisualRunMeasurement(
        text_width=text_width,
        text_block_size=float(treatment.font_size * treatment.line_height),
        leading_advance=leading,
        trailing_advance=trailing,
        visuals=visuals,
    )


def matching_label_visuals(placement_id: str, visual_requests: tuple[Any, ...]) -> tuple[Any, ...]:
    """Bind original label identity before either measurement or omission."""
    matching = []
    for visual in visual_requests:
        if visual.target_kind in {"mark", "axis-band", "axis-label"}:
            continue
        selector = dict(visual.selector)
        target = selector.get("placementId") or visual_target_placement_id(visual.target_kind, selector)
        if placement_id == target or ("placementId" not in selector and placement_id.startswith(target + ":")):
            matching.append(visual)
    return tuple(matching)


def absent_label_visual_sources(absences: tuple[Any, ...], *,
                               visual_requests: tuple[Any, ...],
                               icon_assets: dict[str, Any]) -> frozenset[str]:
    """Validate omitted label bindings without creating icon/text geometry."""
    handled: set[str] = set()
    for absence in absences:
        absence.validate_cache(absence.visibility_index)
        occupied: set[str] = set()
        for visual in matching_label_visuals(absence.placement_id, visual_requests):
            if visual.side in occupied:
                raise LayoutError("E_LAYOUT_VISUAL_DUPLICATE", visual.source_ref)
            occupied.add(visual.side)
            icon = icon_assets.get(visual.ref or "")
            if icon is None or icon.viewport[1] <= 0:
                raise LayoutError("E_ICON_NAME_UNKNOWN", visual.source_ref)
            handled.add(visual.source_ref)
    return frozenset(handled)


def resolve_label_visual_advances(placement_id: str, typography_role: str, *,
                                  visual_requests: tuple[Any, ...], icon_assets: dict[str, Any],
                                  theme_tokens: Any) -> tuple[tuple[Any, Any, float, float], ...]:
    """Resolve closed icon assets and inline advances for one label identity."""
    matching = matching_label_visuals(placement_id, visual_requests)
    if not matching:
        return ()
    found: dict[str, tuple[Any, Any, float, float]] = {}
    size = theme_tokens.text_treatment(typography_role).font_size
    try:
        scale, gap_ratio = theme_tokens.icon_ratios(typography_role)
    except Exception as error:
        raise LayoutError("E_THEME_ICON_RATIO", "/body/visuals") from error
    for visual in matching:
        if visual.side in found:
            raise LayoutError("E_LAYOUT_VISUAL_DUPLICATE", visual.source_ref)
        icon = icon_assets.get(visual.ref or "")
        if icon is None or icon.viewport[1] <= 0:
            raise LayoutError("E_ICON_NAME_UNKNOWN", visual.source_ref)
        height = float(size * scale)
        if height <= 0:
            raise LayoutError("E_THEME_ICON_RATIO", visual.source_ref)
        found[visual.side] = (visual, icon, height * icon.viewport[0] / icon.viewport[1],
                              float(size * gap_ratio))
    return tuple(found[side] for side in ("leading", "trailing") if side in found)


def visual_target_placement_id(kind: str, selector: dict[str, str]) -> str:
    """Map closed View visual targets to completed Layout placement IDs."""
    if kind == "title": return "title"
    if kind == "column" and "id" in selector: return f"column:{selector['id']}"
    if kind == "cell" and {"object", "column"} <= selector.keys(): return f"cell:{selector['object']}:{selector['column']}"
    if kind == "group-header" and "id" in selector: return f"group-header:{selector['id']}"
    if kind == "plot-label" and "id" in selector: return f"member-label:{selector['id']}"
    if kind == "annotation" and "id" in selector: return f"annotation-text:{selector['id']}"
    if kind == "note" and "id" in selector: return f"note:{selector['id']}"
    if kind == "note-index" and "id" in selector: return f"note-index:{selector['id']}"
    if kind == "group-detail" and "id" in selector: return f"group-detail:{selector['id']}"
    if kind == "legend" and "role" in selector: return f"legend:{selector['role']}"
    if kind == "summary" and "panel" in selector and "metric" not in selector: return f"summary:{selector['panel']}"
    if kind == "summary" and {"panel", "metric", "part"} <= selector.keys(): return f"summary:{selector['panel']}:{selector['metric']}:{selector['part']}"
    if kind == "milestone" and "id" in selector: return f"milestone:{selector['id']}"
    if kind == "as-of-label": return "as-of-label"
    if kind == "variance-label" and "object" in selector: return f"variance:{selector['object']}"
    if kind == "mark" and {"object", "facet"} <= selector.keys(): return f"{selector['facet']}:{selector['object']}"
    raise LayoutError("E_LAYOUT_VISUAL_TARGET", "/body/visuals")
