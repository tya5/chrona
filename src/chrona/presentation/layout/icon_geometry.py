"""Normalized vector icon geometry completed in its placed Layout viewport."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class IconPathPlacement:
    commands: tuple[tuple[str, tuple[tuple[float, float], ...]], ...]
    paint: str
    stroke_width: float | None = None
    line_cap: str | None = None
    line_join: str | None = None


def complete_icon_paths(payload: Any, bounds: tuple[float, float, float, float],
                        stroke_scale: float) -> tuple[IconPathPlacement, ...]:
    if payload is None or not hasattr(payload, "viewport") or not hasattr(payload, "paths"):
        missing = tuple(name for name in ("viewport", "paths") if payload is None or not hasattr(payload, name))
        raise ValueError(f"E_PRESENTATION_PRIMITIVE_INVALID: icon payload type={type(payload).__name__} missing required normalized fields={missing!r}")
    vx, vy = payload.viewport
    x, y, width, height = bounds
    if vx <= 0 or vy <= 0:
        raise ValueError(f"E_PRESENTATION_PRIMITIVE_INVALID: icon viewport dimensions ({vx!r}, {vy!r}) must be positive")
    result = []
    for path in payload.paths:
        commands = tuple((command.kind, tuple((x + px * width / vx, y + py * height / vy)
                                               for px, py in command.points))
                         for command in path.commands)
        result.append(IconPathPlacement(commands, path.paint,
                                        path.stroke_width * stroke_scale if path.stroke_width is not None else None,
                                        path.line_cap, path.line_join))
    return tuple(result)
