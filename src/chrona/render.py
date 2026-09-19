from __future__ import annotations

from datetime import date
from html import escape
from .scene import Scene


_LEFT = 180
_TOP = 76
_LANE_HEIGHT = 58
_DAY_WIDTH = 14


def render_svg(scene: Scene, capabilities: set[str] | None = None, settings: dict | None = None) -> str:
    """Render a Scene as deterministic accessible SVG.

    SVG is an adapter output only; it cannot be read back as Project semantics.
    """
    required_capabilities = {"marker", "metadata", "text-alternative"}
    if capabilities is not None and not required_capabilities.issubset(capabilities):
        missing = ", ".join(sorted(required_capabilities - capabilities))
        raise ValueError(f"E_TARGET_CAPABILITY: {missing}")
    placements = scene.placements
    if not placements:
        raise ValueError("Cannot render a project without resolved placements")

    dates = [_placement_dates(value) for value in placements.values()]
    start = min(value[0] for value in dates)
    end = max(value[1] for value in dates)
    span_days = max((end - start).days, 1)
    if settings is None:
        left, top, lane_height, day_width = _LEFT, _TOP, _LANE_HEIGHT, _DAY_WIDTH
        width, height = max(920, left + span_days * day_width + 80), top + len(placements) * lane_height + 70
        font, heading_size, body_size = "system-ui, sans-serif", 20, 13
        background, ink, grid, planned, connector = "#faf8f6", "#1a1a1a", "#e0dbd7", "#c8553d", "#6b7280"
    else:
        viewport, layout, theme = settings["context"]["viewport"], settings["layout"], settings["theme"]
        left, top, lane_height, day_width = layout["margins"]["left"], layout["margins"]["top"], layout["row"]["height"], layout["scale"]["dayWidth"]
        width, height = viewport["width"], viewport["height"]
        font = theme["fontFamily"]; heading_size, body_size = theme["typography"]["heading"]["size"], theme["typography"]["body"]["size"]
        paints, strokes = theme["paints"], theme["strokes"]
        background, ink, grid, planned, connector = paints["background"]["color"], paints["text"]["color"], strokes["axisMinor"]["color"], paints["planned"]["color"], strokes["dependency"]["color"]
        if left + span_days * day_width > width - layout["margins"]["right"] or top + len(placements) * lane_height > height - layout["margins"]["bottom"]:
            raise ValueError("E_LAYOUT_REQUIRED_OVERFLOW")
    title = scene.title
    lanes = {object_id: index for index, object_id in enumerate(placements)}

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc">',
        "<title id=\"title\">" + escape(str(title)) + "</title>",
        "<desc id=\"desc\">" + escape(scene.description) + "</desc>",
        f'<defs><marker id="arrow" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto"><path d="M0,0 L8,4 L0,8 Z" fill="{connector}" /></marker></defs>',
        f'<rect width="{width}" height="{height}" fill="{background}" />',
        f'<text x="{left}" y="{top-heading_size}" font-family="{escape(font, quote=True)}" font-size="{heading_size}" font-weight="700" fill="{ink}">{escape(str(title))}</text>',
    ]

    for offset in range(0, span_days + 1, 7):
        x = left + offset * day_width
        label = start.fromordinal(start.toordinal() + offset).isoformat()
        parts.append(f'<line x1="{x}" y1="{top-24}" x2="{x}" y2="{height - 36}" stroke="{grid}" stroke-width="1" />')
        parts.append(f'<text x="{x + 3}" y="{top-26}" font-family="{escape(font, quote=True)}" font-size="{body_size}">{label}</text>')

    for relation in scene.relations:
        source_id = relation["from"]["object"]
        target_id = relation["to"]["object"]
        if source_id not in lanes or target_id not in lanes:
            continue
        source_x = left + (placements[source_id][relation["from"]["endpoint"]] - start).days * day_width
        target_x = left + (placements[target_id][relation["to"]["endpoint"]] - start).days * day_width
        source_y, target_y = top + lanes[source_id] * lane_height, top + lanes[target_id] * lane_height
        middle_x = max(source_x + 18, (source_x + target_x) // 2)
        parts.append(
            f'<path d="M {source_x} {source_y} H {middle_x} V {target_y} H {target_x}" '
            f'fill="none" stroke="{connector}" stroke-width="1.5" marker-end="url(#arrow)" />'
        )

    for object_id, placement in placements.items():
        lane = lanes[object_id]
        y = top + lane * lane_height
        label = scene.labels[object_id]
        parts.append(f'<text x="{left}" y="{y + 5}" font-family="{escape(font, quote=True)}" font-size="{body_size}" fill="{ink}">{escape(str(label))}</text>')
        if "at" in placement:
            x = left + (placement["at"] - start).days * day_width
            parts.append(f'<circle cx="{x}" cy="{y}" r="7" fill="{planned}" />')
        else:
            x = left + (placement["start"] - start).days * day_width
            end_x = left + (placement["end"] - start).days * day_width
            parts.append(f'<rect x="{x}" y="{y - 11}" width="{max(4, end_x - x)}" height="22" rx="4" fill="{planned}" />')
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
