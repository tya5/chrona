"""Measured inline demand for lane member-name stagger rows."""
from __future__ import annotations

from math import isfinite
from typing import Any

from chrona.presentation.layout.lane_subtracks import LaneItemFootprints, LaneSubtrackPlan
from chrona.presentation.layout.model import geometry_sum
from chrona.presentation.layout.obstacles import obstacle_envelope


def _preflight_error(owner: str, **operands: object) -> ValueError:
    fields = []
    for name, value in operands.items():
        shown = repr(value).replace("\n", " ").replace("\r", " ")[:96]
        fields.append(f"{name}={shown}")
    return ValueError("E_LAYOUT_LANE_LABEL_PREFLIGHT_INPUT: " + owner + " " + ", ".join(fields))


def lane_label_row_requirements(
    measured_labels: tuple[Any, ...],
    scale: Any,
    subtracks: LaneSubtrackPlan,
    mark_footprints: tuple[LaneItemFootprints, ...],
    *,
    timeline_bounds: tuple[float, float],
    row_padding: float = 0.0,
) -> dict[str, float]:
    """Return full row minima, including measured lane-name stagger demand.

    Labels are assigned to the lowest available label row whose inline box
    does not overlap an earlier label. Their inline boxes are derived from the
    completed mark footprints and measured Layout text/chip/visual dimensions.
    End/start side preference follows each measured intent's declared order.
    """
    left, right = timeline_bounds
    if (not isfinite(left) or not isfinite(right) or right <= left
            or not isfinite(row_padding) or row_padding < 0
            or not isinstance(subtracks, LaneSubtrackPlan)
            or not isinstance(mark_footprints, tuple) or not isinstance(measured_labels, tuple)):
        raise _preflight_error("preflight arguments", timeline_bounds=(left, right),
                               row_padding=row_padding,
                               subtracks_type=type(subtracks).__name__,
                               mark_footprints_type=type(mark_footprints).__name__,
                               measured_labels_type=type(measured_labels).__name__)
    # The completed scale is an explicit dependency: reject incomplete or
    # malformed scale records before using any geometry derived from it.
    if (not all(hasattr(scale, field) for field in
                ("scale_id", "origin", "unit_ratio", "range_start", "range_end"))
            or not isfinite(float(scale.origin)) or not isfinite(float(scale.unit_ratio))
            or float(scale.unit_ratio) <= 0):
        raise _preflight_error("scale metrics", scale_id=getattr(scale, "scale_id", None),
                               origin=getattr(scale, "origin", None),
                               unit_ratio=getattr(scale, "unit_ratio", None))

    lane_by_item = {item.item_id: item.lane_id for item in subtracks.items}
    marks_by_item: dict[str, list[tuple[float, float]]] = {}
    for unit in mark_footprints:
        if not isinstance(unit, LaneItemFootprints) or unit.item_id not in lane_by_item:
            raise _preflight_error("mark footprint owner", item_id=getattr(unit, "item_id", None),
                                   lane_id=lane_by_item.get(getattr(unit, "item_id", None)),
                                   footprint_type=type(unit).__name__)
        for facet in unit.facets:
            x1, _, x2, _ = obstacle_envelope(facet.footprint)
            marks_by_item.setdefault(unit.item_id, []).append((x1, x2))

    lanes = {lane.lane_id: lane for lane in subtracks.lanes}
    label_rows: dict[str, list[list[tuple[float, float, float]]]] = {
        lane_id: [] for lane_id in lanes
    }
    ordered = sorted(measured_labels, key=lambda label: (
        getattr(label, "lane_id", ""), getattr(label, "member_id", ""),
        getattr(label, "placement_id", ""),
    ))
    for label in ordered:
        try:
            lane_id = label.lane_id
            member_id = label.member_id
            item_id = label.member_id
            width, height = float(label.width), float(label.height)
            gap = float(label.gap)
            candidates = tuple(label.candidates)
        except (AttributeError, TypeError, ValueError) as error:
            raise _preflight_error("measured lane label", placement_id=getattr(label, "placement_id", None),
                                   member_id=getattr(label, "member_id", None),
                                   lane_id=getattr(label, "lane_id", None),
                                   invalid_field=type(error).__name__) from error
        if (lane_id not in lanes or lane_by_item.get(item_id) != lane_id
                or not member_id or not all(isfinite(value) for value in (width, height, gap))
                or width <= 0 or height <= 0 or gap < 0
                or not candidates):
            raise _preflight_error("measured lane label", placement_id=getattr(label, "placement_id", None),
                                   member_id=member_id, lane_id=lane_id,
                                   width=width, height=height, gap=gap, candidates=candidates)
        anchors = marks_by_item.get(item_id, ())
        if not anchors:
            # There may be an intentionally unmarked member; the temporal
            # scale origin is its deterministic anchor in that case.
            anchor_left = anchor_right = float(scale.origin)
        else:
            anchor_left = min(item[0] for item in anchors)
            anchor_right = max(item[1] for item in anchors)
        options = []
        for side in candidates:
            if side == "end":
                start = anchor_right + gap
                interval = (start, start + width)
            elif side == "start":
                interval = (anchor_left - gap - width, anchor_left - gap)
            else:
                continue
            if interval[0] >= left and interval[1] <= right:
                options.append((side, interval))
        if not options:
            # An infeasible single-row label still consumes a row: the final
            # placement phase can report obstruction, but preflight cannot
            # understate vertical demand because the preferred interval clips.
            side = next((value for value in candidates if value in {"end", "start"}), None)
            if side is None:
                continue
            interval = ((anchor_right + gap, anchor_right + gap + width) if side == "end"
                        else (anchor_left - gap - width, anchor_left - gap))
            options = [(side, interval)]

        rows = label_rows[lane_id]
        # Choose the declared-side interval with the fewest occupied rows;
        # preserve candidate order as the stable tie break.
        scored = []
        for rank, (_side, interval) in enumerate(options):
            row_index = next((index for index, row in enumerate(rows)
                              if all(interval[0] >= existing[1] or existing[0] >= interval[1]
                                     for existing in row)), len(rows))
            scored.append((row_index, rank, interval))
        row_index, _, interval = min(scored, key=lambda item: (item[0], item[1]))
        while len(rows) <= row_index:
            rows.append([])
        rows[row_index].append((interval[0], interval[1], height))

    label_heights: dict[str, list[float]] = {lane_id: [] for lane_id in lanes}
    for label in measured_labels:
        label_heights[label.lane_id].append(float(label.height) + float(label.gap))
    result = {}
    for lane_id, lane in lanes.items():
        extra = geometry_sum(max((item[2] for item in row), default=0.0)
                             for row in label_rows[lane_id])
        # A mark-centred final placement may have cross-side mark and route
        # obstacles that force more levels than inline label overlap alone.
        # One measured level per label is the finite safe demand envelope;
        # fill may then distribute any remaining host block normally.
        result[lane_id] = geometry_sum((
            lane.block_extent, max(extra, geometry_sum(label_heights[lane_id])), row_padding))
    return result
