#!/usr/bin/env python3
"""Check manifest-declared Scene legend keys against their corresponding marks."""
from __future__ import annotations

from collections import defaultdict
import json
import math
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
MARK_PREFIXES = {"planned": "planned:", "actual": "actual:",
                 "snapshot": "snapshot:", "scenario": "scenario:"}


def _paint(item: dict[str, Any]) -> tuple[bool, bool]:
    paint = item.get("paint") or {}
    return paint.get("fill") is not None, paint.get("stroke") is not None


def _surface_findings(primitives: list[dict[str, Any]]) -> list[str]:
    keys: dict[str, dict[str, Any]] = {}
    marks: dict[str, list[dict[str, Any]]] = defaultdict(list)
    progress: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in primitives:
        identifier = item["id"]
        if identifier.startswith("legend-swatch:"):
            role, _, part = identifier.removeprefix("legend-swatch:").partition(":")
            if part in ("", "part0"):
                keys[role] = item
            elif part == "progress-fill":
                keys[f"{role}:progress-fill"] = item
        for role, prefix in MARK_PREFIXES.items():
            if identifier.startswith(prefix):
                marks[role].append(item)
            if identifier.startswith(f"progress-fill:{prefix}"):
                progress[role].append(item)
    findings: list[str] = []
    for role, key in sorted(keys.items()):
        if ":" in role:
            continue
        if key["kind"] == "Path" and role not in {*MARK_PREFIXES, "milestone"}:
            bounds, points = key["bounds"], key.get("points") or []
            inside = all(math.isfinite(x) and math.isfinite(y)
                         and bounds["inline"] - 1e-6 <= x <= bounds["inline"] + bounds["inlineSize"] + 1e-6
                         and bounds["block"] - 1e-6 <= y <= bounds["block"] + bounds["blockSize"] + 1e-6
                         for x, y in points)
            if (not all(math.isfinite(bounds[field]) for field in ("inline", "block", "inlineSize", "blockSize"))
                    or bounds["inlineSize"] == 0 and bounds["blockSize"] == 0 or not inside):
                findings.append(f"{role}: the relation key's bounds {bounds} do not enclose its points")
            continue
        # Plan represents spans; planned points have their own milestone key.
        expected_kind = "Symbol" if role == "milestone" else "Rect"
        candidates = [item for item in marks.get("planned" if role == "milestone" else role, ())
                      if item["kind"] == expected_kind
                      # Baseline ghosts are stroke-only echoes, not the mark the key shows.
                      and ":snapshot:" not in item["id"]]
        if not candidates:
            continue
        if key["kind"] != expected_kind:
            findings.append(f"{role}: key shape is {key['kind']}, its marks are {expected_kind}")
        if _paint(key) != _paint(candidates[0]):
            findings.append(f"{role}: the key paints fill/stroke {_paint(key)}, its marks {_paint(candidates[0])}")
        if key["kind"] == "Rect" and key["bounds"]["inlineSize"] <= key["bounds"]["blockSize"]:
            findings.append(f"{role}: the key {key['bounds']['inlineSize']}x{key['bounds']['blockSize']} is not landscape")
    for role, fills in sorted(progress.items()):
        if role not in keys:
            continue
        fill_key = keys.get(f"{role}:progress-fill")
        if fill_key is None:
            findings.append(f"{role}: the chart draws a progress fill but the Progress key shows none")
        elif fill_key.get("paint") != fills[0].get("paint"):
            findings.append(f"{role}: progress key paint disagrees with its fill")
    return findings


def legend_key_findings(document: dict[str, Any]) -> list[str]:
    """Check surfaces independently; another surface's key cannot satisfy one."""
    surfaces = document["surfaces"]
    if not isinstance(surfaces, list) or not surfaces:
        raise ValueError("Scene must have at least one surface")
    return [finding for surface in surfaces for finding in _surface_findings(surface["primitives"])]


def committed_scene_paths(root: Path = ROOT) -> tuple[Path, ...]:
    from tools.derived_evidence import scene_paths

    return scene_paths(root)


def evaluate_committed_scenes(paths, *, root: Path = ROOT) -> list[dict[str, str]]:
    findings = []
    for path in sorted(paths):
        relative = path.resolve().relative_to(root.resolve()).as_posix()
        try:
            messages = legend_key_findings(json.loads(path.read_text(encoding="utf-8")))
        except (OSError, ValueError, KeyError, TypeError, AttributeError) as error:
            messages = [f"E_LEGEND_KEY_DOCUMENT:{error}"]
        findings.extend({"scene": relative, "finding": message} for message in messages)
    return findings


def main() -> int:
    reconfigure = getattr(sys.stdout, "reconfigure", None)
    if callable(reconfigure):
        reconfigure(encoding="utf-8")
    try:
        paths = committed_scene_paths()
        if not paths:
            raise ValueError("No manifest-declared Scene evidence")
        findings = evaluate_committed_scenes(paths)
    except (OSError, ValueError) as error:
        findings = [{"scene": "", "finding": f"E_LEGEND_KEY_DOCUMENT:{error}"}]
    print(json.dumps({"findings": findings, "errorCount": len(findings)}, ensure_ascii=False, sort_keys=True))
    return int(bool(findings))


if __name__ == "__main__":
    raise SystemExit(main())
