#!/usr/bin/env python3
"""Check committed public Scene evidence with the shared perceptibility evaluator."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable
import argparse
import json
import subprocess
import sys

from chrona.presentation.scene.perceptibility import (
    ScenePerceptibilityError,
    ScenePerceptibilityFinding,
    evaluate_scene_perceptibility,
)


ROOT = Path(__file__).resolve().parents[1]
REPORT_VERSION = "chrona/scene-perceptibility/v1"


def configure_stdout(stream: Any) -> None:
    """Make report bytes portable without changing Unicode finding values."""
    reconfigure = getattr(stream, "reconfigure", None)
    if callable(reconfigure):
        reconfigure(encoding="utf-8")


def committed_scene_paths(root: Path = ROOT) -> tuple[Path, ...]:
    """Return only Git-tracked public generated Scene evidence in stable order."""
    completed = subprocess.run(("git", "-C", str(root), "ls-files", "-z", "examples"), check=False,
                               capture_output=True, text=False)
    if completed.returncode != 0:
        raise RuntimeError("E_SCENE_PERCEPTIBILITY_DOCUMENT: cannot list committed Scene evidence")
    paths = tuple(root / Path(item.decode("utf-8")) for item in completed.stdout.split(b"\0") if item)
    return tuple(path for path in paths if path.match("*/generated/*.scene.json"))


def evaluate_committed_scenes(paths: Iterable[Path], *, root: Path = ROOT) -> tuple[dict[str, Any], ...]:
    """Return stable scene-path/finding records using no evaluator variant."""
    records: list[dict[str, Any]] = []
    for path in sorted(paths):
        relative = path.resolve().relative_to(root.resolve()).as_posix()
        try:
            document = json.loads(path.read_text(encoding="utf-8"))
            findings = evaluate_scene_perceptibility(document)
        except (OSError, ValueError, ScenePerceptibilityError) as error:
            records.append({"scene": relative, "finding": {
                "version": "v1", "code": "E_SCENE_PERCEPTIBILITY_DOCUMENT", "severity": "error",
                "scenePath": "/", "primitiveIds": [], "measuredFacts": {"detail": str(error)},
            }})
            continue
        records.extend({"scene": relative, "finding": finding.as_mapping()} for finding in findings)
    return tuple(records)


def report_document(records: Iterable[dict[str, Any]]) -> dict[str, Any]:
    """Build the tool's stable machine-readable report form."""
    ordered = tuple(records)
    errors = sum(record["finding"]["severity"] == "error" for record in ordered)
    return {"version": REPORT_VERSION, "findings": list(ordered), "errorCount": errors,
            "observationCount": len(ordered) - errors}


def render_human(report: dict[str, Any]) -> str:
    """Render every finding without converting an observation into a baseline."""
    lines: list[str] = []
    for record in report["findings"]:
        finding = record["finding"]
        identities = ",".join(finding["primitiveIds"]) or "-"
        disposition = f" disposition={finding['disposition']}" if "disposition" in finding else ""
        lines.append(f"{finding['severity'].upper()} {finding['code']} {record['scene']} "
                     f"{finding['scenePath']} primitives={identities}{disposition}")
    scenes = len({record["scene"] for record in report["findings"]})
    lines.append(f"Scene perceptibility: {'FAIL' if report['errorCount'] else 'PASS'} "
                 f"({scenes} scenes, {report['errorCount']} errors, {report['observationCount']} observations)")
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
