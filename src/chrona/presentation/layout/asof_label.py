"""Finite, plot-side placement for the required as-of marker label."""
from __future__ import annotations

from math import isfinite

from chrona.presentation.layout.labels import LabelPlacement, LabelRect
from chrona.presentation.layout.obstacles import ObstacleRect, SurfaceObstacleIndex


def find_asof_label_candidate(
    plot_bounds: LabelRect,
    footprint: tuple[float, float],
    *,
    rule_x: float,
    gap: float,
    rule_host_id: str,
    obstacles: SurfaceObstacleIndex,
    obstacle_classes: tuple[str, ...],
) -> LabelPlacement | None:
    """Choose the first legal top-margin or rule-hosted plot position.

    Rule-hosted positions are centered on the vertical as-of rule and searched
    at the plot's top, then at finite contacts with the selected obstacle
    boundaries. Contact generation is independent of obstacle insertion order;
    all acceptance checks use the canonical obstacle index collision predicate.
    """
    width, height = footprint
    if (not all(isfinite(v) for v in (plot_bounds.x, plot_bounds.y,
                                      plot_bounds.width, plot_bounds.height,
                                      width, height, rule_x, gap))
            or plot_bounds.width <= 0 or plot_bounds.height <= 0
            or width <= 0 or height <= 0 or gap < 0):
        raise ValueError("E_LAYOUT_ASOF_LABEL_GEOMETRY")
    if not rule_host_id:
        raise ValueError("E_LAYOUT_ASOF_LABEL_RULE_HOST")

    selected = obstacles.select(classes=obstacle_classes)
    plot_left, plot_top = plot_bounds.x, plot_bounds.y
    plot_right, plot_bottom = plot_bounds.right, plot_bounds.bottom

    def within_plot(box: LabelRect) -> bool:
        return (box.x >= plot_left and box.y >= plot_top
                and box.right <= plot_right and box.bottom <= plot_bottom)

    def legal(box: LabelRect, *, hosted: bool) -> bool:
        if not within_plot(box):
            return False
        return not obstacles.collisions(
            ObstacleRect(box.x, box.y, box.right, box.bottom),
            classes=obstacle_classes,
            rule_host_id=rule_host_id if hosted else None,
        )

    # Preferred: sit beside the rule in the top margin, end side then start.
    top_candidates = (
        ("plot-top-end", LabelRect(rule_x + gap, plot_top + gap, width, height)),
        ("plot-top-start", LabelRect(rule_x - gap - width, plot_top + gap, width, height)),
    )
    for side, box in top_candidates:
        if legal(box, hosted=False):
            return LabelPlacement(side, box)

    # A hosted chip is centered on the rule. Derive a finite set of vertical
    # origins from plot edges and measured-footprint contacts with every
    # required obstacle. The nearest/topmost candidate wins ties.
    hosted_x = rule_x - width / 2
    y_contacts = {plot_top, plot_bottom - height}
    for item in selected:
        geometry = item.geometry
        if isinstance(geometry, ObstacleRect):
            y_contacts.update((geometry.top - item.clearance - height,
                               geometry.bottom + item.clearance))
        else:
            radius = geometry.stroke_width / 2 + item.clearance
            y_contacts.update((min(geometry.start[1], geometry.end[1]) - radius - height,
                               max(geometry.start[1], geometry.end[1]) + radius))
    positions = sorted((y for y in y_contacts if plot_top <= y <= plot_bottom - height),
                       key=lambda y: (abs(y - plot_top), y))
    for y in positions:
        box = LabelRect(hosted_x, y, width, height)
        if legal(box, hosted=True):
            return LabelPlacement("rule-hosted", box)
    return None
