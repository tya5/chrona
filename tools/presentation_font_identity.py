#!/usr/bin/env python3
"""Generate or check exact completed text-font identity evidence."""
from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
from pathlib import Path
import subprocess
import sys
from typing import Any, Iterable, Mapping

from chrona.resources import safe_load
from tools.check_scene_perceptibility import committed_scene_paths


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = Path("docs/diagnostics/presentation-font-identity.md")


@dataclass(frozen=True)
class FontIdentityFinding:
    """One completed text placement checked against its immutable Context."""

    scene: str
    primitive_id: str
    primitive_path: str
    family: str
    weight: int | None
    expected_identity: str | None
    actual_identity: str | None
    code: str
    severity: str

    def as_mapping(self) -> dict[str, Any]:
        return {
            "scene": self.scene, "primitiveId": self.primitive_id,
            "primitivePath": self.primitive_path, "family": self.family,
            "weight": self.weight, "expectedIdentity": self.expected_identity,
            "actualIdentity": self.actual_identity, "code": self.code,
            "severity": self.severity,
        }


def _primary_family(stack: str) -> str:
    return stack.split(",", 1)[0].strip().strip("'\\\"")


def _manifest_contexts(root: Path) -> dict[Path, Path]:
    """Map each tracked generated Scene to the Context that materialized it."""
    contexts: dict[Path, Path] = {}
    completed = subprocess.run(("git", "-C", str(root), "ls-files", "-z", "examples"), check=False,
                               capture_output=True, text=False)
    if completed.returncode != 0:
        raise ValueError("E_FONT_IDENTITY_MANIFEST")
    manifests = tuple(sorted(root / Path(item.decode("utf-8"))
                             for item in completed.stdout.split(b"\0") if item.endswith(b"/manifest.yaml")))
    for manifest_path in manifests:
        try:
            manifest = safe_load(manifest_path.read_bytes())
            slides = manifest.get("slides", ()) if isinstance(manifest, Mapping) else ()
            default = manifest.get("context") if isinstance(manifest, Mapping) else None
        except Exception as error:
            raise ValueError("E_FONT_IDENTITY_MANIFEST") from error
        if not isinstance(slides, list):
            raise ValueError("E_FONT_IDENTITY_MANIFEST")
        for slide in slides:
            if not isinstance(slide, Mapping):
                raise ValueError("E_FONT_IDENTITY_MANIFEST")
            scene = slide.get("expectedScene")
            context = slide.get("context", default)
            if not isinstance(scene, str) or not isinstance(context, str):
                raise ValueError("E_FONT_IDENTITY_MANIFEST")
            scene_path = (manifest_path.parent / scene).resolve()
            context_path = (manifest_path.parent / context).resolve()
            previous = contexts.setdefault(scene_path, context_path)
            if previous != context_path:
                raise ValueError("E_FONT_IDENTITY_MANIFEST")
    return contexts


def _context_catalog(context: Mapping[str, Any]) -> tuple[str, dict[tuple[str, int], str], set[str]]:
    """Return exact declared assets keyed by completed text selection facts."""
    body = context.get("body")
    environment = body.get("environment") if isinstance(body, Mapping) else None
    descriptor = environment.get("fontMetrics") if isinstance(environment, Mapping) else None
    assets = descriptor.get("assets") if isinstance(descriptor, Mapping) else None
    context_id = context.get("id")
    if not isinstance(context_id, str) or not isinstance(assets, list):
        raise ValueError("E_FONT_IDENTITY_CONTEXT")
    catalog: dict[tuple[str, int], str] = {}
    regular_identities: set[str] = set()
    identities: dict[str, tuple[str, int]] = {}
    for asset in assets:
        font = asset.get("font") if isinstance(asset, Mapping) else None
        family = asset.get("family") if isinstance(asset, Mapping) else None
        weight = asset.get("weight") if isinstance(asset, Mapping) else None
        identity = font.get("contentIdentity") if isinstance(font, Mapping) else None
        if not isinstance(family, str) or not isinstance(weight, int) or not isinstance(identity, str):
            raise ValueError("E_FONT_IDENTITY_CONTEXT")
        key = (family.casefold(), weight)
        if key in catalog or (identity in identities and identities[identity] != key):
            raise ValueError("E_FONT_IDENTITY_CONTEXT")
        catalog[key] = identity
        identities[identity] = key
        if weight == 400:
            regular_identities.add(identity)
    return context_id, catalog, regular_identities


def _finding(scene: str, primitive_id: str, primitive_path: str, family: str,
             weight: int | None, expected: str | None, actual: str | None,
             code: str, severity: str) -> FontIdentityFinding:
    return FontIdentityFinding(scene, primitive_id, primitive_path, family, weight,
                               expected, actual, code, severity)


def evaluate_committed_scenes(paths: Iterable[Path], *, root: Path = ROOT,
                              contexts: Mapping[Path, Path] | None = None) -> tuple[dict[str, Any], ...]:
    """Audit every completed text placement from committed Scene evidence."""
    scene_contexts = contexts if contexts is not None else _manifest_contexts(root)
    findings: list[FontIdentityFinding] = []
    for path in sorted(paths):
        scene = path.resolve().relative_to(root.resolve()).as_posix()
        context_path = scene_contexts.get(path.resolve())
        if context_path is None:
            findings.append(_finding(scene, "-", "/", "", None, None, None,
                                     "E_FONT_IDENTITY_CONTEXT", "error"))
            continue
        try:
            document = json.loads(path.read_text(encoding="utf-8"))
            context = safe_load(context_path.read_bytes())
            context_id, catalog, regular_identities = _context_catalog(context)
            resources = document.get("provenance", {}).get("resources", ())
            scene_context = next((item.get("id") for item in resources
                                  if isinstance(item, Mapping) and item.get("kind") == "render-context"), None)
            if scene_context != context_id:
                raise ValueError("E_FONT_IDENTITY_CONTEXT")
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            findings.append(_finding(scene, "-", "/", "", None, None, None,
                                     "E_FONT_IDENTITY_CONTEXT", "error"))
            continue
        surfaces = document.get("surfaces")
        if not isinstance(surfaces, list):
            findings.append(_finding(scene, "-", "/", "", None, None, None,
                                     "E_FONT_IDENTITY_SCENE", "error"))
            continue
        for surface_index, surface in enumerate(surfaces):
            primitives = surface.get("primitives") if isinstance(surface, Mapping) else None
            if not isinstance(primitives, list):
                findings.append(_finding(scene, "-", f"/surfaces/{surface_index}", "", None, None, None,
                                         "E_FONT_IDENTITY_SCENE", "error"))
                continue
            for primitive_index, primitive in enumerate(primitives):
                if not isinstance(primitive, Mapping) or primitive.get("kind") != "Text":
                    continue
                primitive_id = primitive.get("id")
                layout = primitive.get("textLayout")
                location = f"/surfaces/{surface_index}/primitives/{primitive_index}"
                if not isinstance(primitive_id, str) or not isinstance(layout, Mapping):
                    findings.append(_finding(scene, str(primitive_id or "-"), location, "", None, None, None,
                                             "E_FONT_IDENTITY_SCENE", "error"))
                    continue
                family, weight, actual = layout.get("family"), layout.get("weight"), layout.get("assetIdentity")
                if not isinstance(family, str) or not isinstance(weight, int) or not isinstance(actual, str):
                    findings.append(_finding(scene, primitive_id, location, str(family or ""),
                                             weight if isinstance(weight, int) else None,
                                             None, actual if isinstance(actual, str) else None,
                                             "E_FONT_IDENTITY_SCENE", "error"))
                    continue
                expected = catalog.get((_primary_family(family).casefold(), weight))
                if expected is None:
                    code = "E_FONT_IDENTITY_FACE"
                elif weight == 700 and actual in regular_identities:
                    code = "E_FONT_IDENTITY_WEIGHT"
                elif actual != expected:
                    code = "E_FONT_IDENTITY_ASSET"
                else:
                    code = "I_FONT_IDENTITY_EXACT"
                findings.append(_finding(scene, primitive_id, location, family, weight, expected, actual,
                                         code, "error" if code.startswith("E_") else "info"))
    return tuple(item.as_mapping() for item in findings)


def report_document(records: Iterable[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate exact face evidence by completed family/weight selection."""
    grouped: dict[tuple[str, int | None, str | None], list[dict[str, Any]]] = {}
    ordered = tuple(records)
    for record in ordered:
        key = (record["family"], record["weight"], record["expectedIdentity"])
        grouped.setdefault(key, []).append(record)
    rows = []
    for key in sorted(grouped, key=lambda value: (value[0].casefold(), value[1] or -1, value[2] or "")):
        values = grouped[key]
        rows.append({
            "family": key[0], "weight": key[1], "expectedIdentity": key[2],
            "sceneCount": len({item["scene"] for item in values}),
            "placementCount": len(values),
            "errorCount": sum(item["severity"] == "error" for item in values),
        })
    return {
        "version": "chrona/presentation-font-identity/v1", "rows": rows,
        "errorCount": sum(item["severity"] == "error" for item in ordered),
        "findingCount": len(ordered),
        "weight700PlacementCount": sum(item["weight"] == 700 for item in ordered),
        "weight700RegularFaceCount": sum(item["code"] == "E_FONT_IDENTITY_WEIGHT" for item in ordered),
    }


def render_markdown(report: Mapping[str, Any]) -> str:
    """Render one reviewable, checked report without suppressing failures."""
    lines = [
        "# Presentation Font Identity", "",
        "Generated from committed public Scene evidence by tools/presentation_font_identity.py.", "",
        "| Family | Weight | Expected asset | Scenes | Placements | Errors |",
        "| --- | ---: | --- | ---: | ---: | ---: |",
    ]
    for row in report["rows"]:
        display = {**row, "weight": "—" if row["weight"] is None else row["weight"],
                   "expectedIdentity": row["expectedIdentity"] or "—"}
        lines.append("| {family} | {weight} | {expectedIdentity} | {sceneCount} | {placementCount} | {errorCount} |".format(**display))
    lines.extend(("", f"Weight-700 placements: {report['weight700PlacementCount']}.",
                  f"Weight-700 placements measured with a weight-400 identity: {report['weight700RegularFaceCount']}.",
                  f"Findings: {report['findingCount']}; errors: {report['errorCount']}.", ""))
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
            print("E_PRESENTATION_FONT_IDENTITY_REPORT_STALE", file=sys.stderr)
        return 1 if stale or report["errorCount"] else 0
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 1 if report["errorCount"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
