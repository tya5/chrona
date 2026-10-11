"""A mechanical check that every legend key agrees with the marks it names (#499).

Input is a Scene document (the `--emit-scene` JSON). For each `legend-swatch:<role>` whose role has marks on the chart the key
must have the same fill/stroke presence and the same shape family as those marks; a span key must be landscape; a relation key's
bounds must enclose its points; and when the chart draws a progress fill the `actual` key carries one.
"""
from __future__ import annotations

from collections import defaultdict
from typing import Any

# legend role -> (id prefix of its marks on the chart, kinds of those marks that the key imitates)
MARK_PREFIXES = {"planned": "planned:", "actual": "actual:", "snapshot": "snapshot:", "scenario": "scenario:"}


def _paint(item: dict[str, Any]) -> tuple[bool, bool]:
    paint = item.get("paint") or {}
    return paint.get("fill") is not None, paint.get("stroke") is not None


def legend_key_findings(document: dict[str, Any]) -> list[str]:
    primitives = document["surfaces"][0]["primitives"]
    keys: dict[str, dict[str, Any]] = {}
    for item in primitives:
        if item["id"].startswith("legend-swatch:"):
            name = item["id"].removeprefix("legend-swatch:")
            role, _, part = name.partition(":")
            if part in ("", "part0"):  # a glyph key is several parts: its first part is the key
                keys[role] = item
            elif part == "progress-fill":
                keys[f"{role}:progress-fill"] = item
    marks: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in primitives:
        for role, prefix in MARK_PREFIXES.items():
            if item["id"].startswith(prefix):
                marks[role].append(item)
    progress_drawn = any(item["id"].startswith("progress-fill:") for item in primitives)
    findings: list[str] = []
    for role, key in sorted(keys.items()):
        if ":" in role:
            continue  # a part of another key (the progress fill)
        if key["kind"] == "Path":
            bounds, points = key["bounds"], key.get("points") or []
            inside = all(bounds["inline"] - 1e-6 <= x <= bounds["inline"] + bounds["inlineSize"] + 1e-6
                         and bounds["block"] - 1e-6 <= y <= bounds["block"] + bounds["blockSize"] + 1e-6 for x, y in points)
            if bounds["inlineSize"] == 0 and bounds["blockSize"] == 0 or not inside:
                findings.append(f"{role}: the relation key's bounds {bounds} do not enclose its points")
            continue
        for expected_kind in ("Symbol", "Rect"):
            same = [item for item in marks.get(role, ()) if item["kind"] == expected_kind]
            if role == "milestone":
                same = [item for item in marks.get("planned", ()) if item["kind"] == "Symbol"]
            if not same:
                continue
            if role != "milestone" and key["kind"] != expected_kind:
                continue
            if key["kind"] != same[0]["kind"]:
                findings.append(f"{role}: the key is a {key['kind']}, its marks are {same[0]['kind']}")
            elif _paint(key) != _paint(same[0]):
                findings.append(f"{role}: the key paints fill/stroke {_paint(key)}, its marks {_paint(same[0])}")
            if key["kind"] == "Rect" and key["bounds"]["inlineSize"] <= key["bounds"]["blockSize"]:
                findings.append(f"{role}: the key {key['bounds']['inlineSize']}x{key['bounds']['blockSize']} is not landscape")
            break
    if progress_drawn and "actual" in keys and "actual:progress-fill" not in keys:
        findings.append("actual: the chart draws a progress fill but the Progress key shows none")
    return findings
