"""Compile a terse plan to a `timeline/v0.7` Project mapping (Spec 65 section 4), plus a source map.

Pure: text in, one value out. The compiler resolves its own constructs (names, default endpoints, defaults) and
nothing else; it never schedules and it repeats no Core rule. Core validates what it emits.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from chrona.terse.diagnostics import SourceRange, TerseDiagnostic, nearest
from chrona.terse.parser import ObjectStatement, ParseResult, parse

ERROR_LIMIT = 50
PROJECT_VERSION = "timeline/v0.7"
TERSE_VERSION = "0.1"

SourceMap = dict[str, SourceRange]


@dataclass(frozen=True)
class CompileResult:
    """`project` is None whenever `diagnostics` is not empty: a failed compile never yields a partial Project."""

    project: dict[str, Any] | None
    diagnostics: tuple[TerseDiagnostic, ...]
    source_map: SourceMap = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return self.project is not None


def locate(source_map: SourceMap, pointer: str | None) -> SourceRange | None:
    """The best source span for a JSON pointer: its own entry, else the nearest ancestor's."""
    current = pointer or "/"
    while True:
        if current in source_map:
            return source_map[current]
        if "/" not in current.rstrip("/") or current in ("", "/"):
            return None
        current = current.rsplit("/", 1)[0] or "/"


def compile_terse(text: str, source: str | None = None) -> CompileResult:
    parsed = parse(text)
    problems = list(parsed.problems)
    problems.extend(_resolve_names(parsed))
    if problems:
        return CompileResult(None, _finish(problems, source))
    project, source_map = _build(parsed)
    return CompileResult(project, (), source_map)


def _finish(problems: list[TerseDiagnostic], source: str | None) -> tuple[TerseDiagnostic, ...]:
    ordered = sorted(problems, key=lambda item: (item.range.line, item.range.column) if item.range else (0, 0))
    if len(ordered) > ERROR_LIMIT:
        extra = len(ordered) - ERROR_LIMIT
        where = ordered[ERROR_LIMIT].range
        ordered = ordered[:ERROR_LIMIT] + [TerseDiagnostic(
            "E_TERSE_TOO_MANY_ERRORS", f"{extra} more errors are not listed", "/", where, "fix the errors above and compile again")]
    return tuple(item.with_source(source) for item in ordered)


def _resolve_names(parsed: ParseResult) -> list[TerseDiagnostic]:
    """Unknown objects and calendars. Names resolve over the whole file, so forward references are legal (3.6)."""
    problems: list[TerseDiagnostic] = []
    object_names = list(parsed.known_objects)
    calendar_names = list(parsed.known_calendars)

    def calendar(item, extra: str = "") -> None:
        if item is not None and item.value not in parsed.known_calendars:
            close = nearest(item.value, calendar_names)
            hint = f"did you mean `{close}`?" if close else (
                "declare it with `calendar " + item.value + " mon-fri`" if calendar_names == [] else "known calendars: " + ", ".join(calendar_names))
            problems.append(TerseDiagnostic("E_TERSE_CALENDAR_UNKNOWN", f"no calendar named '{item.value}'{extra}", "/", item.range, hint))

    if parsed.project is not None:
        calendar(parsed.project.calendar)
    for statement in parsed.objects:
        calendar(statement.calendar)
        for dep in statement.deps:
            calendar(dep.lag_calendar)
            if dep.name.value not in parsed.known_objects:
                close = nearest(dep.name.value, object_names)
                problems.append(TerseDiagnostic(
                    "E_TERSE_REFERENCE_UNKNOWN", f"no object named '{dep.name.value}'", "/", dep.name.range,
                    f"did you mean `{close}`?" if close else "`after` names an object defined in this plan (forward references are fine)"))
    return problems


def _build(parsed: ParseResult) -> tuple[dict[str, Any], SourceMap]:
    smap: SourceMap = {}
    statement = parsed.project
    assert statement is not None
    project: dict[str, Any] = {"id": statement.id.value}
    smap["/"] = smap["/project"] = smap["/project/id"] = statement.id.range
    if statement.title is not None:
        project["title"] = statement.title.value
        smap["/project/title"] = statement.title.range
    if statement.calendar is not None:
        project["calendar"] = statement.calendar.value
        smap["/project/calendar"] = statement.calendar.range
    elif len(parsed.calendars) == 1:  # N1: the single declared calendar is the project default
        project["calendar"] = parsed.calendars[0].name.value
    result: dict[str, Any] = {"version": PROJECT_VERSION, "project": project}

    if parsed.calendars:
        calendars: dict[str, Any] = {}
        for item in parsed.calendars:
            entry: dict[str, Any] = {"working_days": list(item.days)}
            base = f"/calendars/{item.name.value}"
            smap[base] = item.range
            smap[base + "/working_days"] = item.days_range
            if item.exceptions:
                entry["exceptions"] = []
                for index, (working, when) in enumerate(item.exceptions):
                    entry["exceptions"].append({"date": when.value, "working": working})
                    smap[f"{base}/exceptions/{index}"] = when.range
            calendars[item.name.value] = entry
        result["calendars"] = calendars

    forms = {s.name.value: ("point" if s.schedule.form == "point" else "span") for s in parsed.objects}
    objects: dict[str, Any] = {}
    for item in parsed.objects:
        base = f"/objects/{item.name.value}"
        entry: dict[str, Any] = {"type": item.kind.value}
        smap[base] = item.name.range
        smap[base + "/type"] = item.kind.range
        if item.title is not None:
            entry["title"] = item.title.value
            smap[base + "/title"] = item.title.range
        if item.parent is not None:
            entry["parent"] = item.parent
        if item.calendar is not None:
            entry["calendar"] = item.calendar.value
            smap[base + "/calendar"] = item.calendar_range or item.calendar.range
        entry["schedule"] = _schedule(item, base, smap)
        objects[item.name.value] = entry
    if objects:
        result["objects"] = objects

    relations: list[dict[str, Any]] = []
    used: set[str] = set()
    for item in parsed.objects:
        target_form = forms[item.name.value]
        for dep in item.deps:
            predecessor = dep.name.value
            endpoint = dep.endpoint.value if dep.endpoint is not None else ("at" if forms[predecessor] == "point" else "end")  # N2
            relation_id = base_id = f"{predecessor}-{item.name.value}"  # N4
            counter = 2
            while relation_id in used:
                relation_id = f"{base_id}-{counter}"
                counter += 1
            used.add(relation_id)
            if dep.lag_calendar is not None:
                lag: Any = {"value": dep.lag.value, "calendar": dep.lag_calendar.value}
            else:
                lag = dep.lag.value if dep.lag is not None else "0d"  # N3, N6
            relation = {
                "id": relation_id, "type": "dependency",
                "from": {"object": predecessor, "endpoint": endpoint},
                "to": {"object": item.name.value, "endpoint": "at" if target_form == "point" else "start"},
                "lag": lag,
            }
            index = len(relations)
            relations.append(relation)
            for key in (str(index), relation_id):
                prefix = f"/relations/{key}"
                smap[prefix] = dep.range
                smap[prefix + "/from"] = dep.name.range if dep.endpoint is None else dep.name.range.through(dep.endpoint.range)
                smap[prefix + "/from/object"] = dep.name.range
                smap[prefix + "/from/endpoint"] = dep.endpoint.range if dep.endpoint is not None else dep.name.range
                smap[prefix + "/to"] = smap[prefix + "/to/object"] = smap[prefix + "/to/endpoint"] = item.name.range
                if dep.lag is not None:
                    smap[prefix + "/lag"] = dep.lag.range if dep.lag_calendar is None else dep.lag.range.through(dep.lag_calendar.range)
                    smap[prefix + "/lag/calendar"] = dep.lag_calendar.range if dep.lag_calendar is not None else dep.lag.range
    if relations:
        result["relations"] = relations
    return result, smap


def _schedule(item: ObjectStatement, base: str, smap: SourceMap) -> dict[str, Any]:
    schedule = item.schedule
    smap[base + "/schedule"] = schedule.range
    if schedule.form == "rollup":
        return {"mode": "rollup"}
    if schedule.form == "point":
        return {"mode": "fixed-point", "at": schedule.at}
    if schedule.form == "span":
        return {"mode": "fixed-span", "start": schedule.start, "end": schedule.end}
    assert schedule.amount is not None
    result: dict[str, Any] = {"mode": "scheduled", "amount": schedule.amount.value}
    smap[base + "/schedule/amount"] = schedule.amount.range
    if schedule.anchor is not None:
        which, when = schedule.anchor
        result["anchor"] = {which: when.value}
        smap[base + "/schedule/anchor"] = when.range
    if schedule.bounds:
        constraints: dict[str, dict[str, str]] = {}
        for edge in ("start", "end"):
            for limit in ("min", "max"):
                for name, kind, when in schedule.bounds:
                    if name == edge and kind == limit:
                        constraints.setdefault(edge, {})[limit] = when.value
                        smap[f"{base}/schedule/constraints/{edge}/{limit}"] = when.range
                        smap.setdefault(base + "/schedule/constraints", when.range)
        result["constraints"] = constraints
    return result
