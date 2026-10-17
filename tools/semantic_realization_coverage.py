#!/usr/bin/env python3
"""Generate current semantic-state to completed-Scene-role evidence."""
from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
from pathlib import Path
import tempfile
from typing import Any, Mapping

from chrona.presentation.model.semantic_realization import (
    PurposeClassification, RealizationFamily, purpose_classifications, realization_families,
    validate_purpose_classifications, validate_realization_families)
from chrona.presentation.model.semantic_registry import purposes, semantic_binding, semantic_ids
from tools.derived_artifact_report import report_stale_artifact
from tools.presentation_coverage import Slide, discover, effective_view


class SemanticRealizationCoverageError(ValueError):
    """The committed corpus cannot supply deterministic realization evidence."""


def _view(slide: Slide) -> Mapping[str, Any]:
    return effective_view(slide)


def _primitives(slide: Slide) -> tuple[Mapping[str, Any], ...]:
    try:
        document = json.loads(slide.scene.read_text(encoding="utf-8"))
        return tuple(primitive for surface in document["surfaces"] for primitive in surface["primitives"]
                     if isinstance(primitive, Mapping))
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as error:
        raise SemanticRealizationCoverageError(f"E_PRESENTATION_REALIZATION_SCENE:{slide.scene}") from error


def _table_columns(view: Mapping[str, Any], facet: str) -> frozenset[str]:
    body = view.get("body", {})
    columns = body.get("tableColumns", ()) if isinstance(body, Mapping) else ()
    return frozenset(str(column.get("id")) for column in columns
                     if isinstance(column, Mapping)
                     and isinstance(column.get("source"), Mapping)
                     and (column["source"].get("comparisonFacet") == facet
                          or column["source"].get("facet") == facet)
                     and isinstance(column.get("id"), str))


def _annotation_declarations(view: Mapping[str, Any]) -> tuple[tuple[tuple[str, str], ...], tuple[str, ...]]:
    body = view.get("body", {})
    if not isinstance(body, Mapping):
        raise SemanticRealizationCoverageError("E_PRESENTATION_REALIZATION_VIEW")
    annotations = body.get("annotations", [])
    bindings = body.get("annotationBindings", [])
    if not isinstance(annotations, list) or not isinstance(bindings, list):
        raise SemanticRealizationCoverageError("E_PRESENTATION_REALIZATION_ANNOTATION_SOURCE")
    by_id: list[tuple[str, str]] = []
    for index, annotation in enumerate(annotations):
        if (not isinstance(annotation, Mapping) or not isinstance(annotation.get("id"), str)
                or not annotation["id"] or not isinstance(annotation.get("purpose"), str)):
            raise SemanticRealizationCoverageError(f"E_PRESENTATION_REALIZATION_ANNOTATION_SOURCE:annotations[{index}]")
        by_id.append((annotation["id"], annotation["purpose"]))
    purposes: list[str] = []
    for index, binding in enumerate(bindings):
        if not isinstance(binding, Mapping) or not isinstance(binding.get("purpose"), str):
            raise SemanticRealizationCoverageError(f"E_PRESENTATION_REALIZATION_ANNOTATION_SOURCE:annotationBindings[{index}]")
        purposes.append(binding["purpose"])
    return tuple(by_id), tuple(purposes)


_ANNOTATION_BOX_BINDINGS = {
    "callout": "annotationCalloutBox",
    "highlight": "annotationHighlightBox",
    "note": "annotationNoteBox",
    "explanatory-arrow": "annotationArrowBox",
}


def _evidence(family: RealizationFamily, slides: tuple[Slide, ...]) -> tuple[tuple[str, ...], tuple[str, ...], tuple[str, ...]]:
    states: set[str] = set()
    roles: set[str] = set()
    evidence: set[str] = set()
    for slide in slides:
        view, primitives = _view(slide), _primitives(slide)
        if family.selector.startswith("table-column:comparisonFacet="):
            columns = _table_columns(view, family.selector.rsplit("=", 1)[1])
            if not columns:
                continue
            states.update(family.admitted_states)
            roles.update(str(item.get("visualRole")) for item in primitives
                         if item.get("purpose") == family.primitive_purpose
                         and item.get("tableColumnId") in columns and isinstance(item.get("visualRole"), str))
        elif family.selector == "annotation:purpose":
            annotations, binding_purposes = _annotation_declarations(view)
            ids = {identifier for identifier, purpose in annotations if purpose in family.admitted_states}
            bound_states = {purpose for purpose in binding_purposes if purpose in family.admitted_states}
            if not ids and not bound_states:
                continue
            states.update(purpose for identifier, purpose in annotations if identifier in ids)
            states.update(bound_states)
            roles.update(str(item.get("visualRole")) for item in primitives
                         if item.get("sourceRef") in ids and item.get("purpose") == family.primitive_purpose
                         and isinstance(item.get("visualRole"), str))
            for purpose in bound_states:
                expected_role = semantic_binding(_ANNOTATION_BOX_BINDINGS[purpose]).scene_role
                if any(item.get("purpose") == family.primitive_purpose
                       and item.get("visualRole") == expected_role for item in primitives):
                    roles.add(expected_role)
        else:
            raise SemanticRealizationCoverageError(f"E_PRESENTATION_REALIZATION_SELECTOR:{family.selector}")
        evidence.add(slide.identifier)
    return tuple(sorted(states)), tuple(sorted(roles)), tuple(sorted(evidence))


@dataclass(frozen=True)
class PurposeRow:
    """One registered purpose, derived from the vocabulary and the committed Scenes."""

    purpose: str
    roles: tuple[str, ...]
    slides: tuple[str, ...]
    registered_roles: tuple[str, ...]
    states: tuple[tuple[str, int], ...]
    classification: PurposeClassification


def appearance_role(primitive: Mapping[str, Any]) -> str | None:
    """The effective appearance role: an authored ``themeRole`` selection, else the canonical ``visualRole``."""
    for key in ("themeRole", "visualRole"):
        if isinstance(primitive.get(key), str) and primitive[key]:
            return primitive[key]
    return None


def purpose_rows(slides: tuple[Slide, ...], *, registered: frozenset[str] | None = None,
                 registered_roles: Mapping[str, tuple[str, ...]] | None = None,
                 classifications: tuple[PurposeClassification, ...] | None = None,
                 families: tuple[RealizationFamily, ...] | None = None) -> tuple[PurposeRow, ...]:
    """Derive one row per registered purpose and fail on any unclassified or contradicted row."""
    registered = purposes() if registered is None else registered
    if registered_roles is None:
        found: dict[str, set[str]] = {}
        for identifier in semantic_ids():
            binding = semantic_binding(identifier)
            found.setdefault(binding.purpose, set()).add(binding.scene_role)
        registered_roles = {purpose: tuple(sorted(roles)) for purpose, roles in found.items()}
    by_purpose = validate_purpose_classifications(purpose_classifications() if classifications is None else classifications, registered)
    families = realization_families() if families is None else families
    drawn: dict[str, tuple[set[str], set[str]]] = {}
    for slide in slides:
        for primitive in _primitives(slide):
            purpose, role = primitive.get("purpose"), appearance_role(primitive)
            if not isinstance(purpose, str) or role is None:
                continue
            roles, where = drawn.setdefault(purpose, (set(), set()))
            roles.add(role); where.add(slide.identifier)
    unregistered = sorted(set(drawn) - set(registered))
    if unregistered:
        raise SemanticRealizationCoverageError(f"E_PRESENTATION_PURPOSE_UNREGISTERED:{unregistered!r}")
    rows = []
    for purpose in sorted(registered):
        roles, where = drawn.get(purpose, (set(), set()))
        classification = by_purpose[purpose]
        expected = ("unpainted",) if not roles else (("single-role", "gap") if len(roles) == 1 else ("distinct", "gap"))
        if classification.disposition not in expected:
            raise SemanticRealizationCoverageError(
                f"E_PRESENTATION_PURPOSE_CLASSIFICATION_STALE:purpose={purpose}, classified={classification.disposition}, "
                f"realizedRoles={len(roles)}; expected {' or '.join(expected)}")
        states = tuple((family.family_id, len(family.admitted_states)) for family in families if family.primitive_purpose == purpose)
        rows.append(PurposeRow(purpose, tuple(sorted(roles)), tuple(sorted(where)), tuple(registered_roles.get(purpose, ())), states, classification))
    return tuple(rows)


def single_role_figure(rows: tuple[PurposeRow, ...]) -> tuple[int, int]:
    """Numerator: drawn purposes with exactly one realized role. Denominator: all drawn purposes."""
    drawn = [row for row in rows if row.roles]
    return sum(1 for row in drawn if len(row.roles) == 1), len(drawn)


def _purpose_lines(rows: tuple[PurposeRow, ...]) -> list[str]:
    single, total = single_role_figure(rows)
    unpainted = [row for row in rows if not row.roles]
    lines = ["", "## Purpose coverage", "",
             f"**{single} of {total}** drawn purposes resolve to exactly one realized appearance role; {total - single} resolve to more than one. "
             f"{len(rows)} purposes are registered; {len(unpainted)} are registered but not drawn by any committed Scene and are listed separately, not counted in the denominator.", "",
             "One row per registered purpose, derived from the semantic vocabulary and the committed Scenes. A realized role is the primitive's `themeRole` when it carries one, else its `visualRole`. "
             "Model states come from the family classification below, where one exists. A purpose without a classification fails the check, as does a classification the Scenes contradict.", "",
             "### Drawn purposes", "", "| Purpose | Realized roles | Count | Registered roles | Model states | Disposition | Corpus slides |", "| --- | --- | --- | --- | --- | --- | --- |"]
    for row in rows:
        if row.roles:
            states = ", ".join(f"`{family}` ({count})" for family, count in row.states) or "—"
            lines.append(f"| `{row.purpose}` | " + ", ".join(f"`{role}`" for role in row.roles) + f" | {len(row.roles)} | {len(row.registered_roles)} | {states} | "
                         f"**{row.classification.disposition}**" + (f": {row.classification.reason}" if row.classification.reason else "") + " | " + ", ".join(row.slides) + " |")
    lines.extend(["", "### Registered but unpainted purposes", "", "| Purpose | Registered roles | Reason |", "| --- | --- | --- |"])
    lines.extend(f"| `{row.purpose}` | " + ", ".join(f"`{role}`" for role in row.registered_roles) + f" | {row.classification.reason} |" for row in unpainted)
    if not unpainted:
        lines.append("| — | — | None. |")
    return lines


def render(root: Path) -> str:
    """Render a deterministic registry/View/Scene report; never read adapters."""
    families = realization_families()
    validate_realization_families(families)
    slides = discover(root)
    rows = []
    for family in families:
        states, roles, evidence_slides = _evidence(family, slides)
        intentional = {state for state, _reason in family.intentional_equivalences}
        required = set(states) - intentional
        disposition = "not-selected" if not states else ("gap" if len(roles) < len(required) else "realized")
        reasons = "; ".join(f"{state}: {reason}" for state, reason in family.intentional_equivalences) or "—"
        rows.append((family, states, roles, evidence_slides, disposition, reasons))
    lines = ["# Semantic realization coverage", "", "Generated by `tools/semantic_realization_coverage.py` from the semantic vocabulary, the finite realization registry, View declarations, and committed inspection Scenes. It does not read SVG, PNG, or an adapter.", "",
             "## Current realization evidence", "", "| Family | Declared states | Realized Scene roles | Corpus slides | Disposition | Intentional equivalences |", "| --- | --- | --- | --- | --- | --- |"]
    for family, states, roles, family_slides, disposition, reasons in rows:
        lines.append("| `" + family.family_id + "` | " + ", ".join("`" + state + "`" for state in states) + " | "
                     + (", ".join("`" + role + "`" for role in roles) or "—") + " | "
                     + (", ".join(family_slides) or "—") + " | **" + disposition + "** | " + reasons + " |")
    lines.extend(["", "A `gap` is an admitted, non-equivalent semantic state family whose committed Scene realizes fewer roles than it requires. The corpus fixture may not select every admitted state yet; this is a triage result, not a claim that every distinct model field demands distinct paint."])
    lines.extend(_purpose_lines(purpose_rows(slides)))
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--output", type=Path, default=Path("docs/gallery/semantic-realization-coverage.md"))
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(); root = args.root.resolve(); output = args.output if args.output.is_absolute() else root / args.output
    content = render(root)
    if args.check:
        if not output.is_file() or output.read_text(encoding="utf-8") != content:
            report_stale_artifact(output=output, generated=content, code="E_PRESENTATION_REALIZATION_COVERAGE_STALE",
                                  refresh_argv=("python", "tools/semantic_realization_coverage.py"), root=root)
            raise SystemExit("E_PRESENTATION_REALIZATION_COVERAGE_STALE")
        return
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", newline="\n", dir=output.parent, delete=False) as temporary:
        temporary.write(content); temporary_path = Path(temporary.name)
    temporary_path.replace(output)


if __name__ == "__main__":
    main()
