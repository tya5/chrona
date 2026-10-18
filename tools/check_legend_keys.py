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


def _paint(item: dict[str, Any]) -> tuple[str | None, str | None]:
    paint = item.get("paint") or {}
    return paint.get("fill"), paint.get("stroke")


def _freeze(value: Any) -> Any:
    if isinstance(value, dict):
        return tuple((key, _freeze(item)) for key, item in sorted(value.items()))
    if isinstance(value, list):
        return tuple(_freeze(item) for item in value)
    return value


def _scene_ink_identity(items: list[dict[str, Any]]) -> tuple[Any, ...]:
    """Normalize a Scene figure by fill-first visible palette, opacity and patterns."""
    fills, strokes, patterns = [], [], set()
    for item in items:
        paint = item.get("paint") or {}
        opacity = paint.get("opacity", 1)
        if opacity is None:
            opacity = 1
        if not isinstance(opacity, (int, float)) or not math.isfinite(opacity) or opacity <= 0:
            continue
        fill = paint.get("fill")
        if fill is not None:
            gradient = paint.get("gradient")
            color = ("gradient", _freeze(gradient)) if gradient is not None else ("color", fill.upper() if isinstance(fill, str) else fill)
            fills.append((color, opacity))
        stroke = paint.get("stroke")
        if stroke is not None:
            strokes.append((("color", stroke.upper() if isinstance(stroke, str) else stroke), opacity))
        pattern = item.get("pattern")
        if pattern is not None:
            patterns.add(_freeze(pattern))
    palette = tuple(sorted(set(fills or strokes), key=repr))
    pattern_identity = tuple(sorted(patterns, key=repr)) if patterns else None
    return palette, pattern_identity


def _figure_paint_identity(items: list[dict[str, Any]]) -> tuple[Any, ...]:
    """Retain the complete ordered paint stack for a projected source figure."""
    return tuple((_freeze(item.get("paint") or {}), _freeze(item.get("pattern")))
                 for item in items)


def _figure_groups(items: list[dict[str, Any]]) -> list[list[dict[str, Any]]]:
    """Join only parts with explicit common source and completed bounds."""
    grouped: dict[tuple[Any, ...], list[dict[str, Any]]] = {}
    for index, item in enumerate(items):
        source = item.get("sourceRef")
        bounds = item.get("bounds")
        if item.get("kind") == "Symbol" and isinstance(source, str) and isinstance(bounds, dict):
            identity = ("figure", source, _freeze(bounds))
        else:
            identity = ("primitive", index)
        grouped.setdefault(identity, []).append(item)
    return list(grouped.values())


def _progress_hosts(item: dict[str, Any], marks: dict[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    remainder = item.get("id", "").removeprefix("progress-fill:")
    role = remainder.partition(":")[0]
    candidates = marks.get(role, [])
    clip_source = item.get("clipSourceId")
    if isinstance(clip_source, str):
        return [host for host in candidates
                if host.get("id") == clip_source
                or host.get("id", "").startswith(f"{clip_source}:part")]
    return [host for host in candidates
            if host.get("id") == remainder
            or host.get("id", "").startswith(f"{remainder}:part")]


def _surface_findings(primitives: list[dict[str, Any]], *, legend_declared: bool = True) -> list[str]:
    keys: dict[str, list[dict[str, Any]]] = defaultdict(list)
    progress_keys: list[dict[str, Any]] = []
    marks: dict[str, list[dict[str, Any]]] = defaultdict(list)
    progress: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in primitives:
        identifier = item["id"]
        if identifier.startswith("legend-swatch:"):
            role, separator, suffix = identifier.removeprefix("legend-swatch:").partition(":")
            if role == "progressFill":
                progress_keys.append(item)
            elif separator and suffix == "progress-fill":
                # Read old evidence while keeping the one role-specific Progress key out of its host key.
                progress_keys.append(item)
            else:
                # Keep the complete identity suffix: realized actual-ink groups each have their own digest.
                keys[role].append(item)
        for role, prefix in MARK_PREFIXES.items():
            if identifier.startswith(prefix):
                marks[role].append(item)
            if identifier.startswith(f"progress-fill:{prefix}"):
                progress[role].append(item)
    findings: list[str] = []
    for role, role_keys in sorted(keys.items()):
        if role in {"actual", "milestone"}:
            expected_kind = "Symbol" if role == "milestone" else None
            candidates = [item for item in marks.get("planned" if role == "milestone" else role, ())
                          if (role != "milestone" or item["kind"] == expected_kind)
                          and ":snapshot:" not in item["id"]]
            if not candidates:
                continue
            mark_figures = _figure_groups(candidates)
            mark_inks = {_scene_ink_identity(figure) for figure in mark_figures}
            mark_paints = {_figure_paint_identity(figure) for figure in mark_figures}
            for key_figure in _figure_groups(role_keys):
                if role == "milestone" and any(item["kind"] != expected_kind for item in key_figure):
                    findings.append("milestone: key shape is not Symbol, its marks are Symbol")
                    continue
                matched = (_figure_paint_identity(key_figure) in mark_paints
                           if role == "milestone" else _scene_ink_identity(key_figure) in mark_inks)
                if not matched:
                    key_paint = [_paint(item) for item in key_figure]
                    mark_paint = [_paint(item) for item in candidates]
                    if role == "actual":
                        findings.append(f"actual: key paints figure {key_paint}, no Actual mark has that ink (first mark {mark_paint})")
                    else:
                        findings.append(f"milestone: key paints fill/stroke figure {key_paint}, no source mark figure has that ink (first mark {mark_paint})")
            continue
        for key in role_keys:
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
                          if (role == "actual" or item["kind"] == expected_kind)
                          # Baseline ghosts are stroke-only echoes, not the mark the key shows.
                          and ":snapshot:" not in item["id"]]
            if not candidates:
                continue
            if role != "actual" and key["kind"] != expected_kind:
                findings.append(f"{role}: key shape is {key['kind']}, its marks are {expected_kind}")
            if _paint(key) != _paint(candidates[0]):
                findings.append(f"{role}: the key paints fill/stroke {_paint(key)}, its marks {_paint(candidates[0])}")
            if role != "actual" and key["kind"] == "Rect" and key["bounds"]["inlineSize"] <= key["bounds"]["blockSize"]:
                findings.append(f"{role}: the key {key['bounds']['inlineSize']}x{key['bounds']['blockSize']} is not landscape")
    if any(progress.values()) and not progress_keys and legend_declared:
        distinct_progress = False
        for shapes in progress.values():
            for shape in shapes:
                hosts = _progress_hosts(shape, marks)
                if not hosts or _scene_ink_identity([shape]) not in {
                        _scene_ink_identity(figure) for figure in _figure_groups(hosts)}:
                    distinct_progress = True
                    break
            if distinct_progress:
                break
        if distinct_progress:
            findings.append("Progress: the chart draws a positive progress fill with ink distinct from its host but has no separate Progress key")
    for key in progress_keys:
        candidates = [item for entries in progress.values() for item in entries]
        if key["kind"] == "Rect":
            matching = any(_paint(item) == _paint(key) for item in candidates)
        elif key["kind"] == "Symbol":
            matching = any(_paint(item)[0] == _paint(key)[0] for item in candidates)
        else:  # finite rule-pair keys project selected source stroke only
            matching = any(_paint(item)[1] == _paint(key)[1] for item in candidates)
        if candidates and not matching:
            findings.append(f"Progress: key paint {_paint(key)} disagrees with positive progress marks")
    return findings


def legend_key_findings(document: dict[str, Any]) -> list[str]:
    """Check surfaces independently; another surface's key cannot satisfy one."""
    surfaces = document["surfaces"]
    if not isinstance(surfaces, list) or not surfaces:
        raise ValueError("Scene must have at least one surface")
    return [finding for surface in surfaces for finding in _surface_findings(
        surface["primitives"],
        legend_declared=any(slot.get("source") == "legend" for slot in surface.get("slots", ()))
        if "slots" in surface else True,
    )]


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
