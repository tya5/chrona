"""Validate and schedule one raw Draft Project.

These are the two checks every adapter offers before anything is rendered. A caller
supplies a Project mapping (``*_project``) or the path of one YAML file (``*_file``) and
receives a typed outcome; nothing here reads arguments, prints or exits. A file that
cannot be read or parsed raises the library's own ``OSError`` or ``yaml.YAMLError``,
which ``usecases.failure_report.report_failure`` turns into a diagnostic.

``validate`` reports what structural validation and the Core rules find, then the dependency
cycles the reference scheduler cannot place (``scheduling.dependency_cycles``; #780), without
computing a date. ``schedule`` runs that same check first, so the two commands, and the MCP tools
over these functions, report a cycle identically; it then also rejects what only placement can
find (a fixed date that contradicts its dependencies, a bound that cannot be met).
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Mapping

from chrona.core.deadlines import deadline_warnings
from chrona.core.diagnostics import Diagnostic
from chrona.core.periods import period_range_diagnostics
from chrona.core.source_ranges import attach_ranges
from chrona.core.validation import load_yaml, validate_project
from chrona.scheduling.dependency_cycles import dependency_cycle_diagnostics
from chrona.scheduling.scheduler import schedule
from chrona.usecases.failure_report import diagnostic_record


@dataclass(frozen=True)
class ProjectValidation:
    diagnostics: tuple[Diagnostic, ...]

    @property
    def ok(self) -> bool:
        return not self.diagnostics


@dataclass(frozen=True)
class ProjectSchedule:
    """A scheduling attempt: ``placements`` and ``analysis`` when ``ok``, else ``diagnostics``.

    ``warnings`` are findings about a plan that was scheduled (a ``W_DEADLINE``): they never
    make the attempt not ``ok``, and a rejected attempt has none.
    """

    diagnostics: tuple[Diagnostic, ...]
    placements: dict[str, dict[str, Any]]
    analysis: dict[str, Any] | None
    warnings: tuple[Diagnostic, ...] = ()

    @property
    def ok(self) -> bool:
        return not self.diagnostics

    def payload(self) -> dict[str, Any]:
        """The schedule document: placements, no diagnostics, the warnings and the analysis when derived."""
        payload: dict[str, Any] = {
            "placements": self.placements, "diagnostics": [],
            "warnings": [diagnostic_record(item.id, item.message, "core", item.path, details=item.details, severity="warning")
                         for item in self.warnings],
        }
        if self.analysis is not None:
            payload["analysis"] = self.analysis
        return payload


def _not_a_mapping(project: object) -> Diagnostic | None:
    """A file that parses to a list, a scalar or nothing is a rejected Project, not a tool failure (#782, D8)."""
    if isinstance(project, Mapping):
        return None
    found = "an empty document" if project is None else f"a {type(project).__name__}"
    return Diagnostic("E_SCHEMA", f"a Project must be a YAML mapping with version, project and objects; found {found}", "/")


def validate_project_mapping(project: dict[str, Any]) -> ProjectValidation:
    refused = _not_a_mapping(project)
    if refused is not None:
        return ProjectValidation((refused,))
    diagnostics = tuple(validate_project(project))
    if not diagnostics:  # a cycle is only meaningful in a Project whose relations and objects Core accepted
        diagnostics = dependency_cycle_diagnostics(project)
    return ProjectValidation(diagnostics)


def validate_project_file(path: str | Path) -> ProjectValidation:
    outcome = validate_project_mapping(load_yaml(path))
    return ProjectValidation(attach_ranges(outcome.diagnostics, Path(path).read_text(encoding="utf-8"))) if outcome.diagnostics else outcome


def schedule_project_mapping(project: dict[str, Any]) -> ProjectSchedule:
    """Schedule a Project, serializing the completed result without deriving analysis again."""
    checked = validate_project_mapping(project)  # also refuses a file that is not a mapping (#782, D8)
    if not checked.ok:
        return ProjectSchedule(checked.diagnostics, {}, None)
    result = schedule(project)
    if not result.ok:
        return ProjectSchedule(tuple(result.diagnostics), {}, None)
    ordering = period_range_diagnostics(project, result.placements)  # only placements can order a referenced period (#582)
    if ordering:
        return ProjectSchedule(ordering, {}, None)
    analysis = result.analysis
    derived = None
    if analysis is not None:
        object_order = tuple(project.get("objects", {}))
        derived = {
            "criticalObjectIds": [object_id for object_id in object_order if object_id in analysis.critical],
            "totalFloat": {object_id: {"value": value.value, "unit": value.unit, "calendar": value.calendar}
                           for object_id, value in analysis.total_float.items()},
        }
    return ProjectSchedule((), result.placements, derived, deadline_warnings(project, result.placements))


def schedule_project_file(path: str | Path) -> ProjectSchedule:
    outcome = schedule_project_mapping(load_yaml(path))
    if not outcome.diagnostics:
        return outcome
    return replace(outcome, diagnostics=attach_ranges(outcome.diagnostics, Path(path).read_text(encoding="utf-8")))
