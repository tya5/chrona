#!/usr/bin/env python3
"""Fail when committed Scene evidence ends a legend label with an ellipsis and does not say so (#497).

A legend text that Layout shortens must carry a `W_LAYOUT_TEXT_ELLIPSIZED` diagnostic for the same
primitive, and the surface's fit warning for it must show a natural inline size larger than the
available one. A truncated label with no such record is a silent truncation and fails the check.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable, Mapping
import argparse
import json
import sys


ROOT = Path(__file__).resolve().parents[1]
REPORT_VERSION = "chrona/legend-truncation/v1"
ELLIPSIS = "…"
CODE = "W_LAYOUT_TEXT_ELLIPSIZED"


def configure_stdout(stream: Any) -> None:
    """Make report bytes portable without changing Unicode finding values."""
    reconfigure = getattr(stream, "reconfigure", None)
    if callable(reconfigure):
        reconfigure(encoding="utf-8")


def committed_scene_paths(root: Path = ROOT) -> tuple[Path, ...]:
    """Return every manifest-declared public Scene path, tracked or not."""
    from tools.derived_evidence import scene_paths

    try:
        return scene_paths(root)
    except (OSError, ValueError) as error:
        raise RuntimeError("E_LEGEND_TRUNCATION_DOCUMENT: cannot discover manifest Scene evidence") from error


def _reported_placements(document: Mapping[str, Any]) -> set[str]:
    """The placement ids the Scene's `diagnostics` list reports as ellipsized."""
    placements: set[str] = set()
    for item in document.get("diagnostics", ()):
        code, _, payload = str(item).partition(":")
        if code != CODE:
            continue
        try:
            identity = json.loads(payload)
        except ValueError:
            continue
        if isinstance(identity, Mapping) and isinstance(identity.get("placementId"), str):
            placements.add(identity["placementId"])
    return placements


def _texts(primitive: Mapping[str, Any]) -> tuple[str, ...]:
    layout = primitive.get("textLayout")
    lines = layout.get("lines", ()) if isinstance(layout, Mapping) else ()
    return (str(primitive.get("text", "")), *(str(line) for line in lines))


def evaluate_scene(document: Mapping[str, Any]) -> tuple[dict[str, Any], ...]:
    """Return one error record for each legend text shortened with no or contradicting record."""
    reported = _reported_placements(document)
    findings: list[dict[str, Any]] = []
    for surface in document.get("surfaces", ()):
        facts = {str(item.get("placementId")): item for item in surface.get("fitWarnings", ())
                 if isinstance(item, Mapping) and item.get("code") == CODE}
        for primitive in surface.get("primitives", ()):
            identifier = str(primitive.get("id", ""))
            if (primitive.get("kind") != "Text" or not identifier.startswith("legend:")
                    or not any(text.endswith(ELLIPSIS) for text in _texts(primitive))):
                continue
            if identifier not in reported:
                findings.append({"code": "E_LEGEND_TRUNCATION_UNREPORTED", "severity": "error",
                                 "primitiveId": identifier, "text": str(primitive.get("text", ""))})
                continue
            fact = facts.get(identifier)
            if (fact is None or not isinstance(fact.get("requiredInline"), (int, float))
                    or not isinstance(fact.get("availableInline"), (int, float))
                    or not fact["requiredInline"] > fact["availableInline"]):
                findings.append({"code": "E_LEGEND_TRUNCATION_FACTS", "severity": "error",
                                 "primitiveId": identifier, "text": str(primitive.get("text", ""))})
    return tuple(findings)


def evaluate_committed_scenes(paths: Iterable[Path], *, root: Path = ROOT) -> tuple[dict[str, Any], ...]:
    """Return stable scene-path/finding records for every committed Scene."""
    records: list[dict[str, Any]] = []
    for path in sorted(paths):
        relative = path.resolve().relative_to(root.resolve()).as_posix()
        try:
            findings = evaluate_scene(json.loads(path.read_text(encoding="utf-8")))
        except (OSError, ValueError, AttributeError, TypeError) as error:
            records.append({"scene": relative, "finding": {
                "code": "E_LEGEND_TRUNCATION_DOCUMENT", "severity": "error", "primitiveId": "", "text": str(error)}})
            continue
        records.extend({"scene": relative, "finding": finding} for finding in findings)
    return tuple(records)


def report_document(records: Iterable[dict[str, Any]]) -> dict[str, Any]:
    """Build the tool's stable machine-readable report form."""
    ordered = tuple(records)
    return {"version": REPORT_VERSION, "findings": list(ordered), "errorCount": len(ordered)}


def render_human(report: dict[str, Any]) -> str:
    """Render every finding, then one summary line."""
    lines = [f"ERROR {record['finding']['code']} {record['scene']} "
             f"primitive={record['finding']['primitiveId'] or '-'} text={record['finding']['text']!r}"
             for record in report["findings"]]
    lines.append(f"Legend truncation: {'FAIL' if report['errorCount'] else 'PASS'} "
                 f"({report['errorCount']} errors)")
    return "\n".join(lines)


def main(argv: tuple[str, ...] = tuple(sys.argv[1:])) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--format", choices=("human", "json"), default="human")
    args = parser.parse_args(argv)
    configure_stdout(sys.stdout)
    report = report_document(evaluate_committed_scenes(committed_scene_paths()))
    if args.format == "json":
        print(json.dumps(report, ensure_ascii=False, separators=(",", ":"), sort_keys=True))
    else:
        print(render_human(report))
    return 1 if report["errorCount"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
