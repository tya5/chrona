"""Readable CLI representation of an already validated canonical Scene."""
from __future__ import annotations

import json
from typing import Any


def format_inspection_scene(canonical: bytes) -> bytes:
    """Keep each complete surface primitive on one line without changing data."""
    document = json.loads(canonical)
    return (_format(document, (), 0) + "\n").encode("utf-8")


def _compact(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), allow_nan=False)


def _format(value: Any, path: tuple[str | int, ...], depth: int) -> str:
    indent, child_indent = "  " * depth, "  " * (depth + 1)
    if isinstance(value, dict):
        if not value:
            return "{}"
        members = (child_indent + _compact(key) + ": " + _format(item, (*path, key), depth + 1)
                   for key, item in value.items())
        return "{\n" + ",\n".join(members) + "\n" + indent + "}"
    if isinstance(value, list):
        if not value:
            return "[]"
        primitive_array = (len(path) == 3 and path[0] == "surfaces"
                           and isinstance(path[1], int) and path[2] == "primitives")
        members = (child_indent + (_compact(item) if primitive_array else
                                   _format(item, (*path, index), depth + 1))
                   for index, item in enumerate(value))
        return "[\n" + ",\n".join(members) + "\n" + indent + "]"
    return _compact(value)
