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
    result = []
    for item in items:
        paint = dict(item.get("paint") or {})
        glow, bounds = paint.get("glow"), item.get("bounds")
        if isinstance(glow, dict) and isinstance(bounds, dict) and isinstance(glow.get("region"), dict):
            glow = dict(glow)
            region = glow["region"]
            # The filter rectangle follows the completed figure's placement;
            # compare its physical padding, not absolute chart/key coordinates.
            glow["region"] = tuple(round(value, 9) for value in (
                bounds["inline"] - region["inline"], bounds["block"] - region["block"],
                region["inline"] + region["inlineSize"] - bounds["inline"] - bounds["inlineSize"],
                region["block"] + region["blockSize"] - bounds["block"] - bounds["blockSize"]))
            paint["glow"] = glow
        result.append((_freeze(paint), _freeze(item.get("pattern"))))
    return tuple(result)


def _encoding_witness(item: dict[str, Any]) -> tuple[Any, ...] | None:
    """Return only a complete fill witness; IDs and labels never establish encoding."""
    witness = item.get("encoding")
    if (not isinstance(witness, dict)
            or set(witness) != {"channel", "scaleId", "field", "value", "sources"}
            or witness.get("channel") != "fill"
            or not all(isinstance(witness.get(field), str) and witness[field]
                       for field in ("scaleId", "field", "value"))
            or not isinstance(witness.get("sources"), list) or not witness["sources"]):
        return None
    source_keys: set[tuple[Any, ...]] = set()
    for source in witness["sources"]:
        if not isinstance(source, dict) or source.get("kind") not in {"view", "style"}:
            return None
        required = {"kind", "id", "sourceRef"} | ({"ruleId"} if source["kind"] == "style" else set())
        allowed = required | ({"ruleId"} if source["kind"] == "view" else set())
        if (not required.issubset(source) or not set(source).issubset(allowed)
                or not all(isinstance(source.get(field), str) and source[field]
                           for field in required)):
            return None
        if source["kind"] == "view" and "ruleId" in source:
            return None
        source_keys.add(_freeze(source))
    if len(source_keys) != len(witness["sources"]):
        return None
    return _freeze(witness)


def _legend_coverage(items: list[dict[str, Any]]) -> tuple[str | None, dict[tuple[Any, ...], dict[str, Any]], bool]:
    """Union typed figure coverage, rejecting mixed kinds or malformed witnesses."""
    kinds: set[str] = set()
    witnesses: dict[tuple[Any, ...], dict[str, Any]] = {}
    malformed = False
    for item in items:
        coverage = item.get("legendEncodingCoverage")
        if coverage is None:
            continue
        if (not isinstance(coverage, dict)
                or coverage.get("kind") not in {"state", "encoding"}):
            malformed = True
            continue
        base_keys = {"kind", "witnesses"}
        allowed_keys = (base_keys if coverage["kind"] == "state" else
                        base_keys | ({"paintChannel"} if coverage.get("paintChannel") == "stroke" else set()))
        if set(coverage) != allowed_keys:
            malformed = True
            continue
        kinds.add(coverage["kind"])
        values = coverage.get("witnesses")
        if not isinstance(values, list) or not values:
            malformed = True
            continue
        item_witnesses: set[tuple[Any, ...]] = set()
        for witness in values:
            if _encoding_witness({"encoding": witness}) is None:
                malformed = True
                continue
            frozen = _freeze(witness)
            item_witnesses.add(frozen)
            witnesses[frozen] = witness
        if len(item_witnesses) != len(values):
            malformed = True
    if len(kinds) > 1:
        malformed = True
    return (next(iter(kinds)) if len(kinds) == 1 else None, witnesses, malformed)


def _without_encoded_fill(item: dict[str, Any]) -> tuple[Any, Any]:
    """Normalize only completed fill and its gradient, not other paint/effects."""
    paint = dict(item.get("paint") or {})
    paint.pop("fill", None)
    paint.pop("gradient", None)
    glow, bounds = paint.get("glow"), item.get("bounds")
    if isinstance(glow, dict) and isinstance(bounds, dict) and isinstance(glow.get("region"), dict):
        glow = dict(glow)
        region = glow["region"]
        glow["region"] = tuple(round(value, 9) for value in (
            bounds["inline"] - region["inline"], bounds["block"] - region["block"],
            region["inline"] + region["inlineSize"] - bounds["inline"] - bounds["inlineSize"],
            region["block"] + region["blockSize"] - bounds["block"] - bounds["blockSize"]))
        paint["glow"] = glow
    return _freeze(paint), _freeze(item.get("pattern"))


def _neutral_encoded_figure_matches(
    source: list[dict[str, Any]], key: list[dict[str, Any]],
    declared_witnesses: set[tuple[Any, ...]],
) -> tuple[bool, set[tuple[Any, ...]], dict[tuple[Any, ...], set[Any]]]:
    """Compare ordered parts, relaxing only fill+gradient where source proves fill encoding."""
    if len(source) != len(key):
        return False, set(), {}
    used: set[tuple[Any, ...]] = set()
    fills: dict[tuple[Any, ...], set[Any]] = defaultdict(set)
    for source_part, key_part in zip(source, key):
        witness = _encoding_witness(source_part)
        if witness is not None and witness in declared_witnesses:
            source_fill = (source_part.get("paint") or {}).get("fill")
            if source_fill is None:
                return False, set(), {}
            used.add(witness)
            fills[witness].add(source_fill)
            if (_without_encoded_fill(source_part) != _without_encoded_fill(key_part)
                    or source_part.get("kind") != key_part.get("kind")):
                return False, set(), {}
        elif (_figure_paint_identity([source_part]) != _figure_paint_identity([key_part])
              or source_part.get("kind") != key_part.get("kind")):
            return False, set(), {}
    return bool(used), used, fills


def _admitted_coverage_primitive(item: dict[str, Any], coverage_kind: str | None) -> bool:
    """Match Scene admission for encoding fills and filled-or-stroke state keys."""
    paint = item.get("paint") or {}
    common = (
        item.get("sourceKind") == "legend"
        and item.get("purpose") == "legend-swatch"
        and item.get("kind") in {"Rect", "Symbol", "Path"}
    )
    if coverage_kind == "encoding":
        coverage = item.get("legendEncodingCoverage")
        channel = coverage.get("paintChannel", "fill") if isinstance(coverage, dict) else None
        if channel == "stroke":
            width = paint.get("strokeWidth")
            return (common and paint.get("stroke") is not None
                    and isinstance(width, (int, float)) and not isinstance(width, bool)
                    and math.isfinite(width) and width > 0)
        return common and channel == "fill" and paint.get("fill") is not None
    if coverage_kind == "state":
        return common and (paint.get("fill") is not None or paint.get("stroke") is not None)
    return False


def _encoding_key_paint_inventory(primitives: list[dict[str, Any]]) -> dict[tuple[Any, ...], set[Any]]:
    """Collect each witness's explicitly selected paint from encoding legend keys."""
    candidates = [item for item in primitives
                  if _admitted_coverage_primitive(item, "encoding")]
    fills: dict[tuple[Any, ...], set[Any]] = defaultdict(set)
    for item in candidates:
        kind, witnesses, malformed = _legend_coverage([item])
        if kind != "encoding" or malformed:
            continue
        coverage = item.get("legendEncodingCoverage")
        channel = coverage.get("paintChannel", "fill")
        key_paint = (item.get("paint") or {}).get(channel)
        for witness in witnesses:
            fills[witness].add(key_paint)
    return fills


def _figure_groups(items: list[dict[str, Any]]) -> list[list[dict[str, Any]]]:
    """Join only parts with explicit common source and completed bounds."""
    grouped: dict[tuple[Any, ...], list[dict[str, Any]]] = {}
    for index, item in enumerate(items):
        source = item.get("sourceRef")
        bounds = item.get("bounds")
        if item.get("kind") == "Symbol" and isinstance(source, str) and isinstance(bounds, dict):
            identity = ("figure", source, item.get("purpose"), item.get("visualRole"), _freeze(bounds))
        else:
            identity = ("primitive", index)
        grouped.setdefault(identity, []).append(item)
    return list(grouped.values())


def _point_figure_role(item: dict[str, Any], owner_role: str) -> str | None:
    """Recognize completed point figures, not temporal state (forecast can paint as planned)."""
    role = item.get("visualRole")
    if owner_role == "milestone":
        return role if isinstance(role, str) else "planned"
    if (item.get("kind") == "Symbol" and item.get("sourceKind") == "legend"
            and isinstance(role, str)):
        return role
    return None


def _point_key_findings(visual_role: str, label: str, key_figures: list[list[dict[str, Any]]],
                        surface_primitives: list[dict[str, Any]]) -> list[str]:
    """Match each state key to one complete source mark figure, never a palette union."""
    source_points = [item for item in surface_primitives
                     if item.get("kind") == "Symbol"
                     and item.get("sourceKind") != "legend"
                     and item.get("sourceKind") in {None, "object"}
                     and not item.get("id", "").startswith("legend-swatch:")
                     and (item.get("visualRole") == visual_role
                          or (visual_role == "planned" and item.get("visualRole") is None
                              and item.get("purpose") in {None, "planned"}))
                     and item.get("purpose") != "snapshot"]
    if not source_points:
        return [f"{label}: point key has no source Symbol mark figure"]
    source_figures = _figure_groups(source_points)
    source_paints = {_figure_paint_identity(figure) for figure in source_figures}
    encoding_key_paints = _encoding_key_paint_inventory(surface_primitives)
    findings: list[str] = []
    for key_figure in key_figures:
        if any(item.get("kind") != "Symbol" for item in key_figure):
            findings.append(f"{label}: point key shape is not Symbol")
            continue
        coverage_kind, declared_witnesses, malformed = _legend_coverage(key_figure)
        has_coverage = any("legendEncodingCoverage" in item for item in key_figure)
        if _figure_paint_identity(key_figure) in source_paints and not has_coverage:
            continue

        coverage_parts = [item for item in key_figure if "legendEncodingCoverage" in item]
        malformed = malformed or not coverage_parts or any(
            not _admitted_coverage_primitive(item, coverage_kind) for item in coverage_parts)
        if coverage_kind != "state" or malformed or not declared_witnesses:
            findings.append(
                f"{label}: key paints fill/stroke complete figure {[_paint(item) for item in key_figure]}, "
                "no source point figure has that ordered paint stack"
            )
            findings.append(f"{label}: nonmatching encoded point key lacks valid typed state coverage")
            continue
        declared = set(declared_witnesses)
        matched_witnesses: set[tuple[Any, ...]] = set()
        source_fills: dict[tuple[Any, ...], set[Any]] = defaultdict(set)
        for source_figure in source_figures:
            matched, witnesses, fills = _neutral_encoded_figure_matches(
                source_figure, key_figure, declared)
            if matched:
                matched_witnesses.update(witnesses)
                for witness, values in fills.items():
                    source_fills[witness].update(values)
        if declared != matched_witnesses:
            findings.append(
                f"{label}: key paints fill/stroke complete figure {[_paint(item) for item in key_figure]}, "
                "no source point figure has that ordered paint stack"
            )
            findings.append(f"{label}: state coverage has no matching complete source figure for every witness")
            continue
        for witness in sorted(declared, key=repr):
            fills = source_fills.get(witness, set())
            if (not fills or not any(
                    fill in encoding_key_paints.get(witness, set()) for fill in fills)):
                decoded = dict((key, value) for key, value in witness)
                findings.append(
                    f"{label}: state coverage witness scale={decoded.get('scaleId')!r}, "
                    f"field={decoded.get('field')!r}, value={decoded.get('value')!r} "
                    "has no separate encoding key with the source fill"
                )
        if any(label in finding and ("has no separate encoding key" in finding
                                     or "state coverage" in finding)
               for finding in findings):
            findings.append(
                f"{label}: key paints fill/stroke complete figure {[_paint(item) for item in key_figure]}, "
                "no source point figure has that ordered paint stack"
            )
    return findings


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
        state_key_figures: dict[str, list[list[dict[str, Any]]]] = defaultdict(list)
        ordinary_role_keys: list[dict[str, Any]] = []
        for key in role_keys:
            state = _point_figure_role(key, role)
            if state is None:
                ordinary_role_keys.append(key)
            else:
                state_key_figures[state].append([key])
        # Parts sharing a producer-owned sourceRef form one complete key figure.
        for state in tuple(state_key_figures):
            state_key_figures[state] = [figure for figure in _figure_groups(
                [item for figure in state_key_figures[state] for item in figure])]
            findings.extend(_point_key_findings(
                state, "milestone" if role == "milestone" else state,
                state_key_figures[state], primitives))
        role_keys = ordinary_role_keys
        if not role_keys:
            continue
        if role in {"actual", "milestone"}:
            expected_kind = "Symbol" if role == "milestone" else None
            candidates = [item for item in marks.get("planned" if role == "milestone" else role, ())
                          if (role != "milestone" or item["kind"] == expected_kind)
                          and item.get("purpose") != "snapshot"]
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
                          and item.get("purpose") != "snapshot"]
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
