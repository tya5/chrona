#!/usr/bin/env python3
"""Generate or check finite classified-paint contrast evidence for public Scenes."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import statistics
import sys
from typing import Any, Iterable, Mapping

from chrona.resources import safe_load

from chrona.presentation.scene.contrast_policy import (
    DEFAULT_POLICY,
    SceneContrastFinding,
    SceneContrastPolicyError,
    evaluate_scene_contrast,
)
from chrona.presentation.model.semantic_registry import ContrastClass, contrast_bindings
from tools.check_scene_perceptibility import committed_scene_paths


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = Path("docs/diagnostics/presentation-contrast.md")


OPT_IN = Path("conformance/contrast-opt-in.yaml")


def load_opt_in(root: Path = ROOT) -> frozenset[str]:
    """The Theme ids the repository holds to the contrast floors (#1126); none when the registry is absent."""
    path = root / OPT_IN
    if not path.is_file():
        return frozenset()
    document = safe_load(path.read_bytes()) or {}
    themes = document.get("themes", [])
    if not isinstance(themes, list) or not all(isinstance(item, str) and item for item in themes):
        raise ValueError("E_CONTRAST_OPT_IN_REGISTRY")
    return frozenset(themes)


def scene_theme_id(document: Mapping[str, Any]) -> str | None:
    """The Theme resource id a committed Scene names in its provenance, else nothing."""
    provenance = document.get("provenance")
    resources = provenance.get("resources") if isinstance(provenance, Mapping) else None
    for resource in resources if isinstance(resources, list) else ():
        if isinstance(resource, Mapping) and resource.get("kind") == "theme" and isinstance(resource.get("id"), str):
            return str(resource["id"])
    return None


def evaluate_committed_scenes(paths: Iterable[Path], *, root: Path = ROOT) -> tuple[dict[str, Any], ...]:
    """Collect every classified finding without early exit or baseline suppression.

    A Scene whose Theme the repository has opted in (`conformance/contrast-opt-in.yaml`) is held to the floors:
    marks, state text, ground text and ground that cannot be computed are errors. Any other Scene is evaluated with
    every class at `warning`: contrast constraints are an opt-in design option (#1126).
    """
    records: list[dict[str, Any]] = []
    opted_in = load_opt_in(root)
    for path in sorted(paths):
        relative = path.resolve().relative_to(root.resolve()).as_posix()
        theme = None
        try:
            document = json.loads(path.read_text(encoding="utf-8"))
            theme = scene_theme_id(document)
            held = theme in opted_in
            findings = evaluate_scene_contrast(document, policy=None if held else DEFAULT_POLICY)
        except (OSError, ValueError, SceneContrastPolicyError) as error:
            records.append({"scene": relative, "theme": theme, "optedIn": False, "finding": {
                "code": "E_SCENE_CONTRAST_DOCUMENT", "severity": "error", "scenePath": "/",
                "purpose": "-", "visualRole": "-", "primitiveId": None,
                "contrastRatio": None, "floor": None, "disposition": str(error),
                "groundId": None, "groundColor": None, "paintChannel": None,
                "sampleInline": None, "sampleBlock": None,
                "groundKind": None,
            }})
            continue
        records.extend({"scene": relative, "theme": theme, "optedIn": held, "finding": finding.as_mapping()}
                       for finding in findings)
    return tuple(records)


def report_document(records: Iterable[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate the report's deterministic per-purpose, role, and disposition rows."""
    grouped: dict[tuple[str, str, str, float | None], list[dict[str, Any]]] = {}
    ordered = tuple(records)
    for record in ordered:
        finding = record["finding"]
        key = (finding["purpose"], finding["visualRole"], finding["disposition"], finding["floor"])
        grouped.setdefault(key, []).append(record)
    rows: list[dict[str, Any]] = []
    for key in sorted(grouped):
        values = grouped[key]
        ratios = sorted(item["finding"]["contrastRatio"] for item in values if item["finding"]["contrastRatio"] is not None)
        rows.append({
            "purpose": key[0], "visualRole": key[1], "disposition": key[2], "floor": key[3],
            "slideCount": len({item["scene"] for item in values}),
            "primitiveCount": sum(item["finding"]["primitiveId"] is not None for item in values),
            "minimumContrast": min(ratios) if ratios else None,
            "medianContrast": statistics.median(ratios) if ratios else None,
            "errorCount": sum(item["finding"]["severity"] == "error" for item in values),
            "warningCount": sum(item["finding"]["severity"] == "warning" for item in values),
        })
    decoration_roles = {binding.scene_role for binding in contrast_bindings(ContrastClass.DECORATION)}
    by_scene: dict[str, set[str]] = {}
    corpus_roles: set[str] = set()
    for record in ordered:
        finding = record["finding"]
        if finding["visualRole"] in decoration_roles and finding["disposition"] == "enabled":
            by_scene.setdefault(record["scene"], set()).add(finding["visualRole"])
            corpus_roles.add(finding["visualRole"])
    # A single scene need not carry every decoration role at once, and some
    # roles are never both required: Issue #481 makes groupBand and
    # groupHeaderBand mutually exclusive by design (a group's own band
    # already includes its own header row, so painting a separate header
    # accent under it would only double-tint that row at a contrast the two
    # colours were never chosen against — see the #481 design correction).
    # The witness is corpus-wide (every decoration role evaluated with
    # disposition "enabled" somewhere in the committed public evidence, not
    # all in one scene). Mutually exclusive render alternatives form one
    # required concept: group-band/group-header-band paint a group's body or
    # header, while row-band/row-rule paint the row-decoration choice selected
    # by the View. Every emitted role remains in the findings above.
    mutually_exclusive_groups = (
        {"group-band", "group-header-band"},
        {"row-band", "row-rule"},
    )
    exclusive_members = frozenset().union(*mutually_exclusive_groups)
    required_singly = decoration_roles - exclusive_members
    witnesses = sorted(scene for scene, roles in by_scene.items() if roles == decoration_roles)
    corpus_errors = [] if (required_singly <= corpus_roles
                          and all(group & corpus_roles for group in mutually_exclusive_groups)) else [
        "E_PRESENTATION_CONTRAST_DECORATION_WITNESS"]
    free: dict[str, dict[str, Any]] = {}
    for record in ordered:
        if record.get("optedIn", True):
            continue
        entry = free.setdefault(record.get("theme") or "(no Theme in provenance)",
                                {"scenes": set(), "warnings": 0, "errors": 0})
        entry["scenes"].add(record["scene"])
        entry["warnings"] += record["finding"]["severity"] == "warning"
        entry["errors"] += record["finding"]["severity"] == "error"
    not_opted_in = [{"theme": theme, "sceneCount": len(entry["scenes"]), "warningCount": entry["warnings"],
                     "errorCount": entry["errors"]} for theme, entry in sorted(free.items())]
    return {"version": "chrona/presentation-contrast/v1", "rows": rows, "notOptedIn": not_opted_in,
            "findings": ordered,
            "witnessScenes": witnesses, "corpusErrors": corpus_errors,
            "errorCount": sum(item["finding"]["severity"] == "error" for item in ordered) + len(corpus_errors),
            # A decoration below its floor is a warning (#995): counted and listed, never a failure.
            "warningCount": sum(item["finding"]["severity"] == "warning" for item in ordered),
            "findingCount": len(ordered)}


def render_markdown(report: Mapping[str, Any]) -> str:
    """Render a reviewable report without hiding failed or absent classifications."""
    def number(value: float | None) -> str:
        return "—" if value is None else f"{value:.3f}"
    lines = ["# Presentation Contrast", "", "Generated from committed public Scene evidence by `tools/presentation_contrast.py`.", "",
             "Contrast constraints are an opt-in design option (Specification 46 section 8). For a Theme listed in "
             "`conformance/contrast-opt-in.yaml`, a mark or text below its floor is an error and fails the check; a "
             "decoration below its floor (or on a ground that cannot be read) is a warning. For any other Theme every "
             "miss is a warning: it is listed and counted, and fails nothing.", "",
             "| Purpose | Visual role | Disposition | Floor | Slides | Primitives | Minimum | Median | Errors | Warnings |",
             "| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |"]
    for row in report["rows"]:
        display = dict(row)
        display.update(floor=number(row["floor"]), minimum=number(row["minimumContrast"]),
                       median=number(row["medianContrast"]))
        lines.append("| {purpose} | `{visualRole}` | {disposition} | {floor} | {slideCount} | {primitiveCount} | {minimum} | {median} | {errorCount} | {warningCount} |".format(
            **display))
    lines.extend(("", "## Per-primitive grounds", "",
                  "| Scene | Primitive | Role | Sample | Ground | Ground kind | Ground colour | Channel | Ratio | Floor | Severity |",
                  "| --- | --- | --- | --- | --- | --- | --- | --- | ---: | ---: | --- |"))
    for record in report["findings"]:
        finding = record["finding"]
        if finding["primitiveId"] is None:
            continue
        sample = (f"{finding['sampleInline']:.3f}, {finding['sampleBlock']:.3f}"
                  if finding.get("sampleInline") is not None and finding.get("sampleBlock") is not None else "—")
        lines.append("| `{scene}` | `{primitive}` | `{role}` | {sample} | `{ground}` | {ground_kind} | `{color}` | {channel} | {ratio} | {floor} | {severity} |".format(
            scene=record["scene"], primitive=finding["primitiveId"], role=finding["visualRole"],
            sample=sample,
            ground=finding.get("groundId") or "—", color=finding.get("groundColor") or "—",
            ground_kind=finding.get("groundKind") or "—",
            channel=finding.get("paintChannel") or "—", ratio=number(finding["contrastRatio"]),
            floor=number(finding["floor"]), severity=finding["severity"]))
    lines.extend(("", "## Themes not opted in", "",
                  "Contrast constraints are an opt-in design option (Specification 46 section 8): a Theme listed in "
                  "`conformance/contrast-opt-in.yaml` is held to the floors above, any other Theme only warns.", "",
                  "| Theme | Scenes | Warnings | Errors |", "| --- | ---: | ---: | ---: |",
                  *(f"| `{row['theme']}` | {row['sceneCount']} | {row['warningCount']} | {row['errorCount']} |"
                    for row in report.get("notOptedIn", ()))))
    lines.extend(("", "## Decoration corpus witness", "",
                  "Every non-exclusive decoration role is enabled in committed Scene evidence; "
                  "group-band or group-header-band supplies the group concept, and row-band or row-rule supplies "
                  "the row concept when there are no corpus errors.", "",
                  *(f"- `{scene}`" for scene in report["witnessScenes"]),
                  *(f"- ERROR `{code}`" for code in report["corpusErrors"]),
                  "", f"Findings: {report['findingCount']}; errors: {report['errorCount']}; "
                      f"warnings: {report['warningCount']}.", ""))
    return "\n".join(lines)


def main(argv: tuple[str, ...] = tuple(sys.argv[1:])) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    root = args.root.resolve()
    output = args.output if args.output.is_absolute() else root / args.output
    report = report_document(evaluate_committed_scenes(committed_scene_paths(root), root=root))
    rendered = render_markdown(report)
    stale = not output.is_file() or output.read_text(encoding="utf-8") != rendered
    if args.check:
        if stale:
            print("E_PRESENTATION_CONTRAST_REPORT_STALE", file=sys.stderr)
        return 1 if stale or report["errorCount"] else 0
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 1 if report["errorCount"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
