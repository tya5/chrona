"""The public evidence slides as the manifests declare them, and the reviewed per-slide ledger (#977).

A test never states how many slides, scenes or labels the corpus has. The slides are the ones the
example manifests declare; what each slide shows is compared with its row in
`tests/acceptance/output/public-slide-ledger.yaml`. Adding a slide adds one manifest entry and one
ledger row; changing what a slide shows on purpose edits that slide's row alone.
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
import json
from pathlib import Path
from typing import Any, Mapping
from xml.etree import ElementTree

import yaml

from chrona.resources import safe_load
from tools.derived_evidence import ROOT, manifest_targets

LEDGER = ROOT / "tests/acceptance/output/public-slide-ledger.yaml"
LEDGER_VERSION = "chrona/public-slide-ledger/v0.1"
LEDGER_FIELDS = frozenset({"axisLabels", "dvtHosted", "chips"})
HOSTED_EXAMPLE = "controller-z"


@dataclass(frozen=True)
class DeclaredSlide:
    key: str
    scene: Path | None
    svg: Path
    context: Path | None


@dataclass(frozen=True)
class Observed:
    """What one slide's generated evidence shows, in the terms the ledger records."""

    axis_labels: int
    svg_axis_labels: int
    dvt_hosted: bool
    chips: tuple[str, ...]


def declared_slides(root: Path = ROOT) -> tuple[DeclaredSlide, ...]:
    """Every slide the example manifests declare, in manifest order."""
    slides = []
    # manifest_targets validates the declaration graph. Reuse one decoded
    # document per manifest rather than reparsing it once for every slide.
    manifests: dict[Path, Mapping[str, Any]] = {}
    for manifest_path, slide_id in manifest_targets(root):
        if manifest_path not in manifests:
            value = safe_load(manifest_path.read_bytes())
            if not isinstance(value, Mapping):
                raise ValueError(f"E_PUBLIC_EVIDENCE_MANIFEST:{manifest_path}")
            manifests[manifest_path] = value
        manifest = manifests[manifest_path]
        slide = next(item for item in manifest["slides"] if item["id"] == slide_id)
        base = manifest_path.parent
        scene, context = slide.get("expectedScene"), slide.get("context", manifest.get("context"))
        slides.append(DeclaredSlide(f"{base.name}/{slide_id}", base / scene if scene else None, base / slide["expectedSvg"],
                                    base / context if context else None))
    return tuple(slides)


def _primitives(value: Any, found: dict[str, dict]) -> dict[str, dict]:
    if isinstance(value, dict):
        if isinstance(value.get("id"), str) and "bounds" in value:
            found[value["id"]] = value
        for child in value.values():
            _primitives(child, found)
    elif isinstance(value, list):
        for child in value:
            _primitives(child, found)
    return found


def observe(slide: DeclaredSlide) -> Observed:
    """Read one slide's committed (or snapshot-generated) Scene and SVG."""
    elements = list(ElementTree.parse(slide.svg).getroot())
    svg_axis = sum(1 for item in elements if item.get("data-purpose") == "axis-label")
    hosted = False
    if slide.key.startswith(HOSTED_EXAMPLE + "/"):
        host = next((index for index, item in enumerate(elements) if item.get("data-purpose") == "planned"
                     and item.get("data-source-ref") == "dvt"), None)
        label = next((index for index, item in enumerate(elements) if item.get("data-purpose") == "member-label"
                      and item.get("data-source-ref") == "dvt"), None)
        hosted = host is not None and label is not None
    if slide.scene is None:
        return Observed(svg_axis, svg_axis, hosted, ())
    scene = json.loads(slide.scene.read_bytes())
    axis = sum(1 for surface in scene["surfaces"] for item in surface["primitives"] if item.get("purpose") == "axis-label")
    chips = tuple(sorted(key for key in _primitives(scene, {}) if key.startswith("chip:")))
    return Observed(axis, svg_axis, hosted, chips)


@lru_cache(maxsize=1)
def observe_all() -> dict[str, Observed]:
    return {slide.key: observe(slide) for slide in declared_slides()}


def load_ledger(path: Path = LEDGER) -> dict[str, dict[str, Any]]:
    document = safe_load(path.read_bytes())
    if not isinstance(document, dict) or document.get("version") != LEDGER_VERSION or not isinstance(document.get("slides"), dict):
        raise ValueError(f"E_SLIDE_LEDGER_FORMAT:{path}")
    return document["slides"]


def _row(observed: Observed) -> dict[str, Any]:
    row: dict[str, Any] = {"axisLabels": observed.axis_labels}
    if observed.dvt_hosted:
        row["dvtHosted"] = True
    if observed.chips:
        row["chips"] = list(observed.chips)
    return row


def format_row(key: str, observed: Observed) -> str:
    """The ledger line for one slide, as it is written in the file."""
    return f"{key}: " + yaml.safe_dump(_row(observed), default_flow_style=True, width=10_000, sort_keys=False).strip()


def compare_ledger(observed: Mapping[str, Observed], ledger: Mapping[str, Mapping[str, Any]]) -> list[str]:
    """Every way the slides and the ledger disagree; empty when each slide is accounted for and unchanged."""
    problems: list[str] = []
    for key in sorted(observed.keys() - ledger.keys()):
        problems.append(f"{key}: no ledger row; add `{format_row(key, observed[key])}` if the slide is meant to show this")
    for key in sorted(ledger.keys() - observed.keys()):
        problems.append(f"{key}: ledger row without a manifest slide; remove it")
    for key in sorted(observed.keys() & ledger.keys()):
        row, seen = ledger[key], observed[key]
        unknown = sorted(set(row) - LEDGER_FIELDS)
        if unknown or "axisLabels" not in row:
            problems.append(f"{key}: ledger row must have axisLabels and only {sorted(LEDGER_FIELDS)}; found {sorted(row)}")
            continue
        expected = Observed(row["axisLabels"], row["axisLabels"], bool(row.get("dvtHosted", False)),
                            tuple(sorted(row.get("chips", ()))))
        for name, want, got in (("axisLabels", expected.axis_labels, seen.axis_labels),
                                ("dvtHosted", expected.dvt_hosted, seen.dvt_hosted),
                                ("chips", expected.chips, seen.chips)):
            if want != got:
                problems.append(f"{key}: {name} is {got!r}, the ledger says {want!r}; edit the row only for an intended change")
    return problems


def relation_problems(observed: Mapping[str, Observed]) -> list[str]:
    """Facts that hold with no number: the SVG draws exactly the axis labels the Scene carries."""
    return [f"{key}: the Scene has {seen.axis_labels} axis labels, the SVG draws {seen.svg_axis_labels}"
            for key, seen in sorted(observed.items()) if seen.axis_labels != seen.svg_axis_labels]
