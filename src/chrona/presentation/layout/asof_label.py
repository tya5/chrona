"""Finite, plot-side placement for the required as-of marker label."""
from __future__ import annotations

from math import isfinite

from chrona.presentation.layout.labels import LabelPlacement, LabelRect
from chrona.presentation.layout.obstacles import ObstacleRect, SurfaceObstacleIndex


def _asof_error(code: str, owner: str, **operands: object) -> ValueError:
    fields = []
    for name, value in operands.items():
        shown = repr(value).replace("\n", " ").replace("\r", " ")[:96]
        fields.append(f"{name}={shown}")
    return ValueError(f"{code}: {owner} " + ", ".join(fields))


def find_asof_label_candidate(
    plot_bounds: LabelRect,
    footprint: tuple[float, float],
    *,
    rule_x: float,
    gap: float,
    rule_host_id: str,
    obstacles: SurfaceObstacleIndex,
    obstacle_classes: tuple[str, ...],
    placement: str = "top",
    rows_bottom: float | None = None,
) -> LabelPlacement | None:
    """Choose the first legal top-margin or rule-hosted plot position.

    `below-plot` (#1063) puts the chip outside the plot, in the block Layout reserved under the last row: centred on
    the rule with its top one gap under `rows_bottom` (the last row's bottom, where the plot ends), then beside the rule, all inside the
    timeline slot. When none is legal the search continues with the plot-foot positions, so the caller can report
    the fallback.

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
        raise _asof_error("E_LAYOUT_ASOF_LABEL_GEOMETRY", "as-of chip geometry",
                          plot_bounds=plot_bounds, footprint=footprint, rule_x=rule_x, gap=gap)
    if not rule_host_id:
        raise _asof_error("E_LAYOUT_ASOF_LABEL_RULE_HOST", "as-of rule exemption",
                          rule_host_id=rule_host_id, placement=placement)

    selected = obstacles.select(classes=obstacle_classes)
    plot_left, plot_top = plot_bounds.x, plot_bounds.y
    plot_right, plot_bottom = plot_bounds.right, plot_bounds.bottom
    plot_bottom_slot = plot_bottom

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

    if placement == "below-plot":
        if rows_bottom is None or not isfinite(rows_bottom):
            raise ValueError(f"E_LAYOUT_ASOF_LABEL_GEOMETRY: below-plot needs the finite bottom of the last row, got {rows_bottom!r}")
        top = rows_bottom + gap
        for side, left in (("plot-below-center", rule_x - width / 2), ("plot-below-end", rule_x + gap),
                           ("plot-below-start", rule_x - gap - width)):
            box = LabelRect(left, top, width, height)
            if (box.x >= plot_left and box.right <= plot_right and top >= plot_top
                    and box.bottom <= plot_bottom_slot + 1e-6
                    and not obstacles.collisions(ObstacleRect(box.x, box.y, box.right, box.bottom),
                                                 classes=obstacle_classes,
                                                 rule_host_id=rule_host_id)):
                return LabelPlacement(side, box)
        placement = "foot"

    # Preferred: sit beside the rule in the top margin, end side then start.
    top_candidates = (
        ("plot-top-end", LabelRect(rule_x + gap, plot_top + gap, width, height)),
        ("plot-top-start", LabelRect(rule_x - gap - width, plot_top + gap, width, height)),
    )
    if placement == "foot":
        # The plot foot (#991): centred on the rule just above the plot's last edge, then beside it.
        bottom = plot_bottom - gap - height
        centred = LabelRect(rule_x - width / 2, bottom, width, height)
        if legal(centred, hosted=True):
            return LabelPlacement("plot-bottom-center", centred)
        top_candidates = (
            ("plot-bottom-end", LabelRect(rule_x + gap, bottom, width, height)),
            ("plot-bottom-start", LabelRect(rule_x - gap - width, bottom, width, height)),
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
