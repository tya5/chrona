"""Use case: compile a terse plan to Project YAML bytes, or to positioned diagnostics.

The terse package compiles text to a Project mapping; Core validation (the only owner of Project meaning) runs
here, and its findings are positioned through the compiler's source map. A rejected plan never yields YAML.
"""
from __future__ import annotations

from dataclasses import dataclass

from chrona.core.validation import validate_project
from chrona.terse import SourceMap, TerseDiagnostic, compile_terse, decode, emit_project, locate

# Hints for Core codes live here, not in Core (design 7.6).
CORE_HINTS: dict[str, str] = {
    "E_CALENDAR_REQUIRED": "working-day amounts and lags need a calendar: add `calendar standard mon-fri`; "
                           "with two or more calendars also add `calendar CAL` to the project line",
    "E_INVALID_SPAN": "the end date is exclusive: a span must end after it starts",
    "E_ROLLUP_EMPTY": "a group needs at least one child: indent tasks under it",
    "E_ENDPOINT_MODE_MISMATCH": "a fixed date has only `.at`; a span or group has `.start` and `.end`",
    "E_FIXED_TARGET_VIOLATION": "this fixed date is earlier than its dependencies allow: write the date the message names, "
                                "drop the date to derive it (`NAME gate after X +2wd`), or shorten the `after` dependency "
                                "that pushes past it",
    "E_UNSUPPORTED_CYCLE": "these objects wait on each other: break the loop by removing one `after` dependency",
    "E_UNSATISFIABLE_DEPENDENCIES": "these objects wait on each other with a positive lag: break the loop by removing one `after` dependency",
    "E_CONTRADICTORY_BOUNDS": "a `from`, `until`, `start`/`end` bound or an `at <=` cap contradicts the dates or dependencies around it: "
                              "relax the bound or move the dates",
}


@dataclass(frozen=True)
class PlanCompilation:
    """`yaml` and `project` are present only when `diagnostics` is empty."""

    project: dict | None
    yaml: bytes | None
    diagnostics: tuple[TerseDiagnostic, ...]
    source_map: SourceMap

    @property
    def ok(self) -> bool:
        return self.yaml is not None

    @property
    def defect(self) -> bool:
        """The compiler produced a Project that failed structural validation: a bug, never user input."""
        return any(item.id == "E_TERSE_COMPILER_DEFECT" for item in self.diagnostics)


def emit_project_text(project: dict) -> str:
    """The deterministic Project YAML of a compiled mapping (the one emitter, shared with the table importer)."""
    return emit_project(project)


def compile_plan(data: bytes, source: str | None = None) -> PlanCompilation:
    """Decode, compile and validate one terse plan. Never raises for any input bytes."""
    text, problem = decode(data)
    if text is None:
        assert problem is not None
        return PlanCompilation(None, None, (problem.with_source(source),), {})
    compiled = compile_terse(text, source)
    if compiled.project is None:
        return PlanCompilation(None, None, compiled.diagnostics, compiled.source_map)
    findings = validate_project(compiled.project)
    if findings:
        positioned = tuple(_position(item, compiled.source_map, source) for item in findings)
        return PlanCompilation(None, None, positioned, compiled.source_map)
    return PlanCompilation(compiled.project, emit_project(compiled.project).encode("utf-8"), (), compiled.source_map)


def _position(finding, source_map: SourceMap, source: str | None, component: str = "core") -> TerseDiagnostic:
    if finding.id == "E_SCHEMA":
        return TerseDiagnostic("E_TERSE_COMPILER_DEFECT", f"the compiled Project failed structural validation: {finding.message}",
                               finding.path, locate(source_map, finding.path), "report this plan as a chrona bug", source)
    pointer = finding.path
    where = pointer
    if finding.id == "E_CALENDAR_REQUIRED" and pointer and pointer.count("/") == 2:
        where = pointer + "/schedule/amount"  # Core reports the object; the amount word is what to fix
    return TerseDiagnostic(finding.id, finding.message, pointer, locate(source_map, where),
                           CORE_HINTS.get(finding.id), source, component)


def position_findings(compilation: PlanCompilation, findings, source: str | None, component: str = "core") -> tuple[TerseDiagnostic, ...]:
    """Position Core or scheduler findings on the plan a compiled Project came from (design 9.2).

    A finding's pointer names the compiled Project; the source map turns it into the line the author edits.
    """
    return tuple(_position(item, compilation.source_map, source, component) for item in findings)


def input_unreadable(source: str, reason: str) -> TerseDiagnostic:
    """The plan could not be read (exit 2); the CLI adapter reports it in the same shape as every compile finding."""
    return TerseDiagnostic("E_TERSE_INPUT_IO", f"cannot read the plan {source}: {reason}", "/", None,
                           "check the path, or pass - to read the plan from standard input", source)


def output_exists(destination: str) -> TerseDiagnostic:
    """`-o` never replaces a file (design D9): a re-compile must not silently erase hand edits."""
    return TerseDiagnostic("E_TERSE_OUTPUT_EXISTS", f"{destination} already exists and compile does not overwrite", "/", None,
                           "delete the file first if you mean to replace it, or choose another name")
