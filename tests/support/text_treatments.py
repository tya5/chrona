"""Synthetic fixtures for the #585 text treatments (horizontal compression, vertical writing).

A Project goes through the packaged preset bundle with a Theme that declares a treatment on a few roles.
Nothing here reads `examples/`.
"""
from __future__ import annotations

from typing import Any, Iterable, Mapping

def with_scale(parts: dict[str, dict[str, Any]], roles: Iterable[str] | None = None, value: Any = 0.6, *,
               token: str = "h-scale") -> list[str]:
    """Bind `horizontalScale` to a number token on each named role (default: every role that has a font size)."""
    theme = parts["theme"]["body"]
    declared = [role for role, binding in theme["roles"].items() if "fontSize" in binding and (roles is None or role in roles)]
    theme["values"][token] = {"type": "number", "value": value}
    for role in declared:
        theme["roles"][role]["horizontalScale"] = token
    return declared


def texts(rendered: Any) -> dict[str, Any]:
    """The Text primitives of a render by scene id."""
    return {item.scene_id: item for item in rendered.surface.primitives if item.kind.value == "Text"}


def widths(rendered: Any) -> Mapping[str, float]:
    return {scene_id: item.bounds[2] for scene_id, item in texts(rendered).items()}
