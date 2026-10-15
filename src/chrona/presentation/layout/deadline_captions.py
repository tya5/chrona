"""Place optional deadline copy in remaining space, never moving prior content."""
from __future__ import annotations

from dataclasses import dataclass, replace
from decimal import Decimal
from typing import Any

from chrona.presentation.layout.model import Rect
from chrona.presentation.layout.obstacles import ObstacleRect, SurfaceObstacle, SurfaceObstacleIndex
from chrona.presentation.layout.surface_quality import CollisionDomain, ShapePlacement, TextPlacement
from chrona.presentation.layout.text import place_text
from chrona.presentation.model.diagnostic_sources import DiagnosticProvenance, DiagnosticSubject
from chrona.presentation.model.info_diagnostics import DeadlineCaptionsDropped


@dataclass(frozen=True)
class DeadlineCaptionAnchor:
    placement_id: str
    source_ref: str
    host_placement_id: str
    content: str
    tick_x: float
    run_end: float
    run_y: float
    stroke_margin: float
    subjects: tuple[DiagnosticSubject, ...]


@dataclass(frozen=True)
class DeadlineCaptionBatch:
    text: tuple[TextPlacement, ...] = ()
    info: tuple[DeadlineCaptionsDropped, ...] = ()
    provenance: tuple[DiagnosticProvenance, ...] = ()


def place_deadline_captions(*, anchors: tuple[DeadlineCaptionAnchor, ...], plot: Rect,
                           shapes: tuple[ShapePlacement, ...], obstacles: SurfaceObstacleIndex,
                           theme_tokens: Any, font_metrics: Any) -> DeadlineCaptionBatch:
    if not anchors:
        return DeadlineCaptionBatch()
    role = "deadline-caption" if theme_tokens.has_role("deadline-caption") else "text"
    inventory = obstacles.copy()
    # Deadline strokes have one shared Theme treatment. Reserve their maximum
    # paint envelope locally; do not change earlier routing/label decisions.
    margin = anchors[0].stroke_margin
    for shape in shapes:
        if shape.semantic_id not in {"deadlineMark", "deadlineMarkOutline"}:
            continue
        padding = margin if shape.semantic_id == "deadlineMark" else 0
        left, top, width, height = (float(shape.bounds.inline), float(shape.bounds.block),
                                    float(shape.bounds.inline_size), float(shape.bounds.block_size))
        if width + 2 * padding > 0 and height + 2 * padding > 0:
            inventory.add(SurfaceObstacle("caption-ink:" + shape.placement_id, "rule", "timeline",
                ObstacleRect(left - padding, top - padding, left + width + padding, top + height + padding)))
    left, top = float(plot.inline), float(plot.block)
    right, bottom = left + float(plot.inline_size), top + float(plot.block_size)
    placed: list[TextPlacement] = []
    dropped: list[DeadlineCaptionAnchor] = []
    for anchor in anchors:
        measured = place_text(
            placement_id=anchor.placement_id, source_ref=anchor.source_ref, content=anchor.content,
            inline=0, baseline_block=0, typography_role=role, theme_tokens=theme_tokens,
            font_metrics=font_metrics, slot_id="timeline", semantic_id="deadlineCaption",
            collision_region="timeline", collision_domain=CollisionDomain("timeline", "content"))
        gap = max(1.0, measured.font_size / 4) + anchor.stroke_margin
        width, height = float(measured.bounds.inline_size), float(measured.bounds.block_size)
        y = anchor.run_y - height / 2
        for x in (anchor.run_end + gap, anchor.tick_x - gap - width):
            bounds = ObstacleRect(x, y, x + width, y + height)
            if x < left or y < top or bounds.right > right or bounds.bottom > bottom:
                continue
            if inventory.collisions(bounds):
                continue
            dy = y - float(measured.bounds.block)
            accepted = replace(measured,
                bounds=Rect(Decimal(str(x)), Decimal(str(y)), measured.bounds.inline_size, measured.bounds.block_size),
                baseline=(x, measured.baseline[1] + dy), subjects=anchor.subjects)
            placed.append(accepted)
            inventory.add(SurfaceObstacle(anchor.placement_id, "text", "timeline", bounds))
            break
        else:
            dropped.append(anchor)
    if not dropped:
        return DeadlineCaptionBatch(tuple(placed))
    info = DeadlineCaptionsDropped("table-timeline", len(dropped))
    subjects = tuple(dict.fromkeys(subject for anchor in dropped for subject in anchor.subjects))
    return DeadlineCaptionBatch(tuple(placed), (info,), (DiagnosticProvenance(info.scene_diagnostic(), subjects),))
