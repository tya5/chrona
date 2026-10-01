"""Validate and schedule one raw Draft Project.

These are the two checks every adapter offers before anything is rendered. A caller
supplies a Project mapping (``*_project``) or the path of one YAML file (``*_file``) and
receives a typed outcome; nothing here reads arguments, prints or exits. A file that
cannot be read or parsed raises the library's own ``OSError`` or ``yaml.YAMLError``,
which ``usecases.failure_report.report_failure`` turns into a diagnostic.

``validate`` reports what structural validation and the Core rules find; it does not
schedule, so a cyclic Project validates. ``schedule`` is the stricter check: it also
rejects what the reference scheduler cannot place (for example an unsupported cycle).
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from chrona.core.deadlines import deadline_warnings
from chrona.core.diagnostics import Diagnostic
from chrona.core.validation import load_yaml, validate_project
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


def validate_project_mapping(project: dict[str, Any]) -> ProjectValidation:
    return ProjectValidation(tuple(validate_project(project)))


def validate_project_file(path: str | Path) -> ProjectValidation:
    return validate_project_mapping(load_yaml(path))


def schedule_project_mapping(project: dict[str, Any]) -> ProjectSchedule:
    """Schedule a Project, serializing the completed result without deriving analysis again."""
    result = schedule(project)
    if not result.ok:
        return ProjectSchedule(tuple(result.diagnostics), {}, None)
    analysis = result.analysis
    derived = None
    if analysis is not None:
        object_order = tuple(project.get("objects", {}))
        derived = {
            "criticalObjectIds": [object_id for object_id in object_order if object_id in analysis.critical],
            "totalFloat": analysis.total_float,
        }
    return ProjectSchedule((), result.placements, derived, deadline_warnings(project, result.placements))


def schedule_project_file(path: str | Path) -> ProjectSchedule:
    return schedule_project_mapping(load_yaml(path))
