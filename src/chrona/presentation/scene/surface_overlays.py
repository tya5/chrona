"""Projection of completed canvas treatments and their Scene-owned paint order."""
from __future__ import annotations

from dataclasses import replace

from chrona.presentation.layout.canvas_overlays import CanvasOverlays
from chrona.presentation.model.theme_tokens import ThemeTokenView
from chrona.presentation.scene.model import ScenePrimitive, SceneSlot, SceneSurface
from chrona.presentation.scene.paint import resolve_radial_overlay_paint
from chrona.presentation.scene.pattern_geometry import project_pattern_placement
from chrona.presentation.scene.visual_capabilities import VisualProfile


def project_canvas_overlays(surface: SceneSurface, placements: CanvasOverlays | None,
                            tokens: ThemeTokenView, profile: VisualProfile | None) -> SceneSurface:
    """Copy Layout geometry after content, radial first and sparse ink last."""
    if placements is None or (placements.radial is None and placements.pattern is None):
        return surface
    primitives = list(surface.primitives)
    slots = list(surface.slots)
    information = list(surface.info_diagnostics)
    order = max((item.paint_order for item in primitives), default=0)
    for placement in (placements.radial, placements.pattern):
        if placement is None:
            continue
        role = placement.placement_id
        rect = placement.slot.bounds
        bounds = (float(rect.inline), float(rect.block), float(rect.inline_size), float(rect.block_size))
        paint = None
        pattern = None
        if placement is placements.radial:
            resolution = resolve_radial_overlay_paint(tokens, placement, visual_profile=profile)
            information.extend(resolution.omissions)
            if resolution.paint is None:
                continue
            paint = resolution.paint
        else:
            pattern = project_pattern_placement(placement.pattern)
        order += 1
        slots.append(SceneSlot(placement.slot.slot_id, role, None, bounds))
        primitives.append(ScenePrimitive(
            role, "Rect", role, "decoration", role, role, bounds,
            slot_id=placement.slot.slot_id, paint_order=order, paint=paint, pattern=pattern,
            visual_capability_source_ref=f"/body/roles/{role}"))
    return replace(surface, slots=tuple(slots), primitives=tuple(primitives), info_diagnostics=tuple(information))
