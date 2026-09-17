from __future__ import annotations

from datetime import date
from html import escape
from typing import Any

from .scheduler import ScheduleResult


_LEFT = 180
_TOP = 76
_LANE_HEIGHT = 58
_DAY_WIDTH = 14


def render_svg(project: dict[str, Any], result: ScheduleResult) -> str:
    """Render scheduled placements as a small, deterministic SVG timeline.

    This is intentionally a derived projection: it consumes schedule placements
    and never stores or interprets SVG coordinates as project semantics.
    """
    placements = result.placements
    if not placements:
        raise ValueError("Cannot render a project without resolved placements")

    dates = [_placement_dates(value) for value in placements.values()]
    start = min(value[0] for value in dates)
    end = max(value[1] for value in dates)
    span_days = max((end - start).days, 1)
    width = max(920, _LEFT + span_days * _DAY_WIDTH + 80)
    height = _TOP + len(placements) * _LANE_HEIGHT + 70
    title = project.get("project", {}).get("title") or project.get("project", {}).get("id", "Chrona timeline")
    lanes = {object_id: index for index, object_id in enumerate(placements)}

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc">',
        "<title id=\"title\">" + escape(str(title)) + "</title>",
        "<desc id=\"desc\">Timeline rendered from Chrona semantic project data.</desc>",
        "<defs><marker id=\"arrow\" markerWidth=\"8\" markerHeight=\"8\" refX=\"7\" refY=\"4\" orient=\"auto\"><path d=\"M0,0 L8,4 L0,8 Z\" fill=\"#6b7280\" /></marker></defs>",
        f'<rect width="{width}" height="{height}" fill="#faf8f6" />',
        f'<text x="24" y="34" font-family="system-ui, sans-serif" font-size="20" font-weight="700" fill="#1a1a1a">{escape(str(title))}</text>',
    ]

    for offset in range(0, span_days + 1, 7):
        x = _x(start, start, offset)
        label = start.fromordinal(start.toordinal() + offset).isoformat()
        parts.append(f'<line x1="{x}" y1="52" x2="{x}" y2="{height - 36}" stroke="#e0dbd7" stroke-width="1" />')
        parts.append(f'<text x="{x + 3}" y="50" font-family="system-ui, sans-serif" font-size="10" fill="#6b6b6b">{label}</text>')

    for relation in project.get("relations", []):
        source_id = relation["from"]["object"]
        target_id = relation["to"]["object"]
        if source_id not in lanes or target_id not in lanes:
            continue
        source_x = _endpoint_x(start, placements[source_id], relation["from"]["endpoint"])
        target_x = _endpoint_x(start, placements[target_id], relation["to"]["endpoint"])
        source_y = _lane_y(lanes[source_id])
        target_y = _lane_y(lanes[target_id])
        middle_x = max(source_x + 18, (source_x + target_x) // 2)
        parts.append(
            f'<path d="M {source_x} {source_y} H {middle_x} V {target_y} H {target_x}" '
            'fill="none" stroke="#6b7280" stroke-width="1.5" marker-end="url(#arrow)" />'
        )

    for object_id, placement in placements.items():
        item = project.get("objects", {}).get(object_id, {})
        lane = lanes[object_id]
        y = _lane_y(lane)
        label = item.get("title") or object_id
        parts.append(f'<text x="24" y="{y + 5}" font-family="system-ui, sans-serif" font-size="13" fill="#1a1a1a">{escape(str(label))}</text>')
        if "at" in placement:
            x = _endpoint_x(start, placement, "at")
            parts.append(f'<circle cx="{x}" cy="{y}" r="7" fill="#c8553d" />')
        else:
            x = _endpoint_x(start, placement, "start")
            end_x = _endpoint_x(start, placement, "end")
            parts.append(f'<rect x="{x}" y="{y - 11}" width="{max(4, end_x - x)}" height="22" rx="4" fill="#c8553d" />')
    parts.append("</svg>")
    return "\n".join(parts) + "\n"


def _placement_dates(placement: dict[str, date]) -> tuple[date, date]:
    if "at" in placement:
        return placement["at"], placement["at"]
    return placement["start"], placement["end"]


def _x(origin: date, value: date, offset: int = 0) -> int:
    return _LEFT + ((value - origin).days + offset) * _DAY_WIDTH


def _endpoint_x(origin: date, placement: dict[str, date], endpoint: str) -> int:
    return _x(origin, placement[endpoint])


def _lane_y(index: int) -> int:
    return _TOP + index * _LANE_HEIGHT
