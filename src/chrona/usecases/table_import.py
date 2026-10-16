"""Use case: import a plan from a CSV or TSV table (#1307).

One row is one object. The table is turned into a terse plan (Spec 65) and compiled by the one compiler, so the Project is
the one `chrona compile` produces for that plan, and every finding of the compiler and of Core validation is mapped back from
the generated plan line to the cell of the table. The columns the terse syntax cannot say become the Project's `fields` and an
Actual Set. Nothing here reads or writes a file: the adapter gives text and takes values.
"""
from __future__ import annotations

import csv
import io
import re
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Any, Iterable, Mapping

from chrona.resources import safe_load, schema_document
from chrona.scheduling.dependency_cycles import find_dependency_cycles
from chrona.usecases.project_checks import validate_project_mapping
from chrona.usecases.terse_compile import compile_plan, emit_project_text

COLUMNS = ("id", "title", "type", "start", "end", "finish", "duration", "parent", "predecessors", "deadline", "calendar",
           "progress", "actual_start", "actual_finish")
"""The closed column vocabulary. Headers match case-insensitively; spaces and hyphens read as underscores."""

CALENDAR_HINT = ('working-day amounts need a calendar: pass --calendar "standard mon-fri" to `chrona import` '
                 "(repeat --calendar for more; the first is the project default)")
_SLUG = re.compile(r"[^a-z0-9]+")
_ISO = re.compile(r"\d{4}-\d{2}-\d{2}")
_PROGRESS = re.compile(r"\s*(\d+(?:\.\d+)?)\s*(%?)\s*")
ERROR_LIMIT = 50


@dataclass(frozen=True)
class ImportDiagnostic:
    """One finding at a cell: `row` is the 1-based line of the table (the header is row 1), `column` the 1-based cell."""

    code: str
    message: str
    row: int | None = None
    column: int | None = None
    header: str | None = None
    hint: str | None = None
    source: str | None = None
    source_ref: str | None = None

    def as_dict(self) -> dict[str, Any]:
        where = f" (row {self.row}, column {self.column} `{self.header}`)" if self.row and self.column else (
            f" (row {self.row})" if self.row else "")
        record: dict[str, Any] = {"code": self.code, "severity": "error", "component": "import", "sourceRef": self.source_ref or "/",
                                  "message": self.message + where}
        if self.row is not None:
            record["cell"] = {key: value for key, value in (("row", self.row), ("column", self.column), ("header", self.header))
                              if value is not None}
        if self.hint:
            record["hint"] = self.hint
        if self.source:
            record["source"] = self.source
        return record


@dataclass(frozen=True)
class ImportResult:
    project_yaml: bytes | None
    actual_yaml: bytes | None
    diagnostics: tuple[ImportDiagnostic, ...]

    @property
    def ok(self) -> bool:
        return self.project_yaml is not None


@dataclass
class _Row:
    number: int
    cells: dict[str, str]
    columns: dict[str, int]
    fields: dict[str, str] = field(default_factory=dict)
    field_columns: dict[str, int] = field(default_factory=dict)

    def get(self, name: str) -> str:
        return self.cells.get(name, "").strip()


def field_role_vocabulary() -> tuple[str, ...]:
    """The closed Project field-role vocabulary, read from the schema that owns it (never restated here)."""
    return tuple(schema_document("vocabulary-v0.1.schema.yaml")["$defs"]["projectFieldRole"]["enum"])


def _bind_roles(roles: Iterable[str], header_kinds: Mapping[str, str]) -> tuple[dict[str, str], list[ImportDiagnostic]]:
    """`ROLE=HEADER` bindings to imported extra columns, or the findings that refuse them (#1584, #1585)."""
    vocabulary = field_role_vocabulary()
    bound: dict[str, str] = {}
    problems: list[ImportDiagnostic] = []
    for text in roles:
        role, separator, header = text.partition("=")
        role, header = role.strip(), header.strip()
        if not separator or not role or not header:
            problems.append(ImportDiagnostic("E_IMPORT_ROLE_SYNTAX", f"--role '{text}' is not ROLE=HEADER",
                                             hint="write --role responsible=team"))
        elif role not in vocabulary:
            problems.append(ImportDiagnostic("E_IMPORT_ROLE_UNKNOWN", f"'{role}' is not a field role",
                                             hint="roles: " + ", ".join(vocabulary)))
        elif role in bound:
            problems.append(ImportDiagnostic("E_IMPORT_ROLE_DUPLICATE", f"--role {role} is given twice",
                                             hint="bind each role to one header"))
        elif header not in header_kinds:
            problems.append(ImportDiagnostic("E_IMPORT_ROLE_HEADER_ABSENT", f"--role {role}={header}: the table has no `{header}` header",
                                             hint="headers: " + ", ".join(header_kinds)))
        elif header_kinds[header]:
            problems.append(ImportDiagnostic("E_IMPORT_ROLE_COLUMN_RESERVED",
                                             f"--role {role}={header}: `{header}` is the `{header_kinds[header]}` column, not an extra field",
                                             hint="bind a column the import vocabulary does not use, such as `team`"))
        else:
            bound[role] = header
    return bound, problems


def slug(text: str, fallback: str = "plan") -> str:
    """A project id from free text: lower-case letters, digits and hyphens, starting with a letter."""
    value = _SLUG.sub("-", text.lower()).strip("-") or fallback
    return value if value[0].isalpha() else f"{fallback}-{value}"


def _canonical(header: str, mapping: Mapping[str, str]) -> str | None:
    key = re.sub(r"[\s-]+", "_", header.strip().lower())
    key = mapping.get(header.strip(), mapping.get(key, key))
    return key if key in COLUMNS else None


def read_table(text: str, delimiter: str, mapping: Mapping[str, str] | None = None
               ) -> tuple[list[_Row], list[ImportDiagnostic], list[str], dict[str, str]]:
    """Rows keyed by canonical column name; unknown headers are kept as `fields`.

    The last item maps every header of the table to its canonical column name, or to "" for an extra (field) header."""
    mapping = mapping or {}
    problems: list[ImportDiagnostic] = []
    reader = csv.reader(io.StringIO(text.lstrip("﻿"), newline=""), delimiter=delimiter)
    rows = [(reader.line_num, record) for record in reader]
    if not rows:
        return [], [ImportDiagnostic("E_IMPORT_EMPTY", "the table is empty", hint="start with a header row such as `id,title,type,start,end`")], [], {}
    header_number, headers = rows[0]
    header_number = 1
    columns: dict[str, int] = {}
    extra: dict[int, str] = {}
    header_kinds: dict[str, str] = {}
    for index, header in enumerate(headers, start=1):
        name = _canonical(header, mapping)
        if header.strip():
            header_kinds.setdefault(header.strip(), name or "")
        if name is None:
            if header.strip():
                extra[index] = header.strip()
        elif name in columns:
            problems.append(ImportDiagnostic("E_IMPORT_COLUMN_DUPLICATE", f"the column `{name}` appears twice", 1, index, header.strip()))
        else:
            columns[name] = index
    for required in ("id",):
        if required not in columns:
            problems.append(ImportDiagnostic("E_IMPORT_COLUMN_MISSING", f"the table has no `{required}` column", 1,
                                             hint="columns: " + ", ".join(COLUMNS)))
    if "end" in columns and "finish" in columns:
        problems.append(ImportDiagnostic("E_IMPORT_COLUMN_CONFLICT", "`end` (exclusive) and `finish` (inclusive) are both present; use one",
                                         1, columns["finish"], "finish"))
    parsed: list[_Row] = []
    for number, record in rows[1:]:
        if not any(cell.strip() for cell in record):
            continue
        if len(record) > len(headers):
            problems.append(ImportDiagnostic("E_IMPORT_ROW_TOO_LONG", f"the row has {len(record)} cells, the header {len(headers)}",
                                             number, len(headers) + 1, "",
                                             "quote a cell that contains the delimiter"))
        cells = {name: (record[index - 1] if index <= len(record) else "") for name, index in columns.items()}
        item = _Row(number, cells, columns)
        for index, header in extra.items():
            value = record[index - 1].strip() if index <= len(record) else ""
            if value:
                item.fields[header] = value
                item.field_columns[header] = index
        parsed.append(item)
    return parsed, problems, [name for name in COLUMNS if name in columns], header_kinds


def _piece_line(pieces: list[tuple[str, str | None]], indent: int) -> tuple[str, list[tuple[int, int, str | None]]]:
    """Join (text, header) pieces: a piece starting with `\x00` is glued to the previous one, others get a space."""
    text = " " * indent
    spans: list[tuple[int, int, str | None]] = []
    for piece, header in pieces:
        glued = piece.startswith("\x00")
        piece = piece.lstrip("\x00")
        if text.strip() and not glued:
            text += " "
        start = len(text) + 1
        text += piece
        spans.append((start, len(text) + 1, header))
    return text, spans


def _date_plus_one(value: str) -> str:
    try:
        return (date.fromisoformat(value) + timedelta(days=1)).isoformat() if _ISO.fullmatch(value) else value
    except ValueError:
        return value  # the compiler reports the bad date at its own cell


def _quote(title: str) -> str:
    return '"' + " ".join(title.split()).replace("\\", "\\\\").replace('"', '\\"') + '"'


def _schedule_pieces(row: _Row, kind: str, has_after: bool) -> list[tuple[str, str | None]]:
    start, end, finish, duration = row.get("start"), row.get("end"), row.get("finish"), row.get("duration")
    if kind == "group":
        return []
    if finish:
        end, end_header = _date_plus_one(finish), "finish"
    else:
        end_header = "end"
    if start and end:
        return [(start, "start"), ("\x00..", None), ("\x00" + end, end_header)]
    if duration and start:
        return [(duration, "duration"), ("from", None), (start, "start")]
    if duration and end:
        return [(duration, "duration"), ("until", None), (end, end_header)]
    if duration:
        return [(duration, "duration")]
    if start:
        return [(start, "start")]
    if end:
        return [(end, end_header)]
    return []


def _order(rows: list[_Row], problems: list[ImportDiagnostic]) -> list[tuple[_Row, int]]:
    """Rows in plan order with their depth: a child follows its group (stable within a parent)."""
    by_id: dict[str, _Row] = {}
    for row in rows:
        identifier = row.get("id")
        if identifier in by_id and identifier:
            problems.append(ImportDiagnostic("E_IMPORT_ID_DUPLICATE", f"the id '{identifier}' is already used on row {by_id[identifier].number}",
                                             row.number, row.columns["id"], "id"))
        elif identifier:
            by_id[identifier] = row
        else:
            problems.append(ImportDiagnostic("E_IMPORT_ID_MISSING", "the row has no id", row.number, row.columns["id"], "id"))
    children: dict[str, list[_Row]] = {}
    roots: list[_Row] = []
    for row in rows:
        identifier = row.get("id")
        if not identifier or by_id.get(identifier) is not row:
            continue
        parent = row.get("parent")
        if not parent:
            roots.append(row)
        elif parent not in by_id:
            close = _nearest(parent, list(by_id))
            problems.append(ImportDiagnostic("E_IMPORT_PARENT_UNKNOWN", f"no row has the id '{parent}'", row.number, row.columns["parent"],
                                             "parent", f"did you mean `{close}`?" if close else None))
            roots.append(row)
        else:
            children.setdefault(parent, []).append(row)
    ordered: list[tuple[_Row, int]] = []
    seen: set[str] = set()

    def visit(row: _Row, depth: int) -> None:
        identifier = row.get("id")
        seen.add(identifier)
        ordered.append((row, depth))
        for child in children.get(identifier, ()):
            visit(child, depth + 1)

    for row in roots:
        visit(row, 0)
    for row in rows:  # what is left sits in a parent cycle
        identifier = row.get("id")
        if identifier and by_id.get(identifier) is row and identifier not in seen:
            problems.append(ImportDiagnostic("E_IMPORT_PARENT_CYCLE", f"'{identifier}' is its own ancestor through `parent`",
                                             row.number, row.columns["parent"], "parent"))
            seen.add(identifier)
    return ordered


def _nearest(word: str, known: list[str]) -> str | None:
    from chrona.core.suggestions import nearest
    return nearest(word, known)


def _progress(value: str) -> float | None:
    match = _PROGRESS.fullmatch(value)
    if match is None:
        return None
    number = float(match.group(1))
    number = number / 100 if match.group(2) or number > 1 else number
    return round(number, 6) if 0 <= number <= 1 else None


@dataclass
class _Plan:
    lines: list[str] = field(default_factory=list)
    spans: dict[int, tuple[_Row, list[tuple[int, int, str | None]]]] = field(default_factory=dict)


def _generate(ordered: list[tuple[_Row, int]], preface: list[str]) -> _Plan:
    plan = _Plan(list(preface))
    for row, depth in ordered:
        kind = row.get("type").lower() or "task"
        predecessors = row.get("predecessors")
        pieces: list[tuple[str, str | None]] = [(row.get("id"), "id")]
        title = row.get("title")
        if title:
            pieces.append((_quote(title), "title"))
        pieces.append((kind, "type"))
        pieces.extend(_schedule_pieces(row, kind, bool(predecessors)))
        if row.get("calendar"):
            pieces.extend([("calendar", None), (row.get("calendar"), "calendar")])
        if predecessors:
            pieces.extend([("after", None), (predecessors, "predecessors")])
        if row.get("deadline"):
            pieces.extend([("deadline", None), (row.get("deadline"), "deadline")])
        text, spans = _piece_line(pieces, depth * 2)
        plan.lines.append(text)
        plan.spans[len(plan.lines)] = (row, spans)
    return plan


def _locate(plan: _Plan, line: int | None, column: int | None, code: str = "") -> tuple[int | None, int | None, str | None]:
    entry = plan.spans.get(line or 0)
    if entry is None:
        return None, None, None
    row, spans = entry
    chosen = None
    for start, end, header in spans:
        if header is not None and start <= (column or 0) < max(end, start + 1):
            chosen = header
            break
    if chosen is None:
        chosen = "parent" if code in {"E_TERSE_CHILDREN_NOT_ALLOWED", "E_TERSE_INDENT"} and row.get("parent") else "id"
    index = row.columns.get(chosen) or row.field_columns.get(chosen) or row.columns["id"]
    return row.number, index, chosen


def import_table(text: str, *, delimiter: str = ",", project_id: str, title: str | None = None, calendars: Iterable[str] = (),
                 as_of: str | None = None, mapping: Mapping[str, str] | None = None, source: str | None = None,
                 roles: Iterable[str] = ()) -> ImportResult:
    """Convert a table to Project YAML (and an Actual Set when it has actual columns). Reports every row error in one run.

    `roles` are `ROLE=HEADER` bindings of Project `fieldRoles` to extra columns (#1584). The Project then goes through the one
    Project validation (`validate`, `render`) and the Actual Set through the Actual contract, each finding mapped to its cell (#1585)."""
    rows, problems, _present, header_kinds = read_table(text, delimiter, mapping)
    bound_roles, role_problems = _bind_roles(roles, header_kinds)
    problems.extend(role_problems)
    if "E_IMPORT_COLUMN_MISSING" in {item.code for item in problems} or "E_IMPORT_EMPTY" in {item.code for item in problems}:
        return ImportResult(None, None, _finish(problems, source))
    preface = ["terse 0.1", f"project {project_id} {_quote(title or project_id)}", *[f"calendar {item}" for item in calendars]]
    ordered = _order(rows, problems)
    plan = _generate(ordered, preface)
    compiled = compile_plan("\n".join(plan.lines).encode("utf-8") + b"\n", source)
    seen_calendar_hint = False
    for item in compiled.diagnostics:
        line = item.range.line if item.range is not None else None
        column = item.range.column if item.range is not None else None
        row, index, header = _locate(plan, line, column, item.id)
        message = item.message
        if row is None and item.range is not None and item.range.line <= len(preface):
            message = f"{message} (the generated project or calendar line)"
        hint = item.hint
        if item.id == "E_CALENDAR_REQUIRED":  # plan syntax is wrong here: say it once, as the import option
            hint = None if seen_calendar_hint else CALENDAR_HINT
            seen_calendar_hint = True
        problems.append(ImportDiagnostic(item.id, message, row, index, header, hint, source))
    if problems:
        return ImportResult(None, None, _finish(problems, source))
    project = compiled.project
    assert project is not None
    objects = project.get("objects", {})
    for row, _depth in ordered:
        if row.fields:
            objects[row.get("id")]["fields"] = dict(row.fields)
    if bound_roles:
        project["fieldRoles"] = dict(bound_roles)
    problems.extend(_project_findings(project, ordered))
    observations, actual_problems = _observations(ordered)
    problems.extend(actual_problems)
    actual_yaml = _actual_yaml(project_id, as_of, observations) if observations else None
    if actual_yaml is not None and not actual_problems:
        problems.extend(_actual_findings(project_id, actual_yaml, ordered))
    if as_of is not None and not _valid_date(as_of):
        problems.append(ImportDiagnostic("E_IMPORT_AS_OF_INVALID", f"--as-of '{as_of}' is not a YYYY-MM-DD date"))
    if problems:
        return ImportResult(None, None, _finish(problems, source))
    project_yaml = emit_project_text(project).encode("utf-8")
    return ImportResult(project_yaml, actual_yaml, ())


def _project_findings(project: dict[str, Any], ordered: list[tuple[_Row, int]]) -> list[ImportDiagnostic]:
    """The Project validation `validate` and `render` run (Core rules, then dependency cycles), at the cells that caused it."""
    by_id = {row.get("id"): row for row, _depth in ordered}
    found: list[ImportDiagnostic] = []
    for item in validate_project_mapping(project).diagnostics:
        row, column, header, hint, path = None, None, None, None, item.path
        pointer = (item.path or "").split("/")
        if item.id in {"E_UNSUPPORTED_CYCLE", "E_UNSATISFIABLE_DEPENDENCIES"}:
            for cycle in find_dependency_cycles(project):
                if cycle.closing_endpoints and item.path == cycle.diagnostic().path:
                    source_id, target_id = cycle.closing_endpoints
                    target = by_id.get(target_id)
                    if target is not None and "predecessors" in target.columns:
                        row, column, header = target.number, target.columns["predecessors"], "predecessors"
                        hint = f"remove `{source_id}` from the predecessors of `{target_id}`, or another link of the loop"
        elif len(pointer) > 2 and pointer[1] == "objects" and pointer[2] in by_id:
            target = by_id[pointer[2]]
            row, column, header = target.number, target.columns["id"], "id"
        found.append(ImportDiagnostic(item.id, item.message, row, column, header, hint, None, path))
    return found


def _actual_findings(project_id: str, actual_yaml: bytes, ordered: list[tuple[_Row, int]]) -> list[ImportDiagnostic]:
    """The Actual Set contract `render` applies to the generated Actual Set, reported at the row and column of the value."""
    from chrona.presentation.contracts import ClosureIdentity, ContractError
    from chrona.presentation.contracts.resources import parse_contract
    document = safe_load(actual_yaml)
    try:
        parse_contract(ClosureIdentity("actual-set", str(document["id"]), "draft", "sha256:import"), document)
    except ContractError as error:
        match = re.fullmatch(r"/body/observations/(\d+)(?:/actual/(\w+))?.*", error.source_ref or "")
        rows = {row.get("id"): row for row, _depth in ordered}
        observation = document["body"]["observations"][int(match.group(1))] if match else None
        row = rows.get(observation["projectObjectId"]) if observation else None
        header = {"start": "actual_start", "finish": "actual_finish"}.get(match.group(2) or "", None) if match else None
        if row is None or header is None or header not in row.columns:
            return [ImportDiagnostic(error.diagnostic_id, error.detail or error.diagnostic_id, row.number if row else None,
                                     row.columns["id"] if row else None, "id" if row else None)]
        message = error.detail
        if error.diagnostic_id == "E_ACTUAL_FINISH_NOT_AFTER_START":
            message = f"actual_finish {row.get('actual_finish')} is before actual_start {row.get('actual_start')}"
        return [ImportDiagnostic(error.diagnostic_id, message, row.number, row.columns[header], header,
                                 "actual_finish is the last day worked (inclusive), on or after actual_start")]
    return []


def _valid_date(value: str) -> bool:
    try:
        return bool(_ISO.fullmatch(value)) and bool(date.fromisoformat(value))
    except ValueError:
        return False


def _observations(ordered: list[tuple[_Row, int]]) -> tuple[list[dict[str, Any]], list[ImportDiagnostic]]:
    observations: list[dict[str, Any]] = []
    problems: list[ImportDiagnostic] = []
    for row, _depth in ordered:
        actual: dict[str, Any] = {}
        point = row.get("type").lower() == "gate"
        for column, key in (("actual_start", "at" if point else "start"), ("actual_finish", "at" if point else "finish")):
            value = row.get(column)
            if not value:
                continue
            if not _valid_date(value):
                problems.append(ImportDiagnostic("E_IMPORT_DATE_INVALID", f"'{value}' is not a real YYYY-MM-DD date", row.number,
                                                 row.columns[column], column, "write the date as 2027-03-05"))
            else:
                # `actual_finish` is inclusive like `finish`; the Actual Set `finish` is exclusive (#1565). A gate's `at` is a date.
                actual.setdefault(key, _date_plus_one(value) if key == "finish" else value)
        if row.get("progress"):
            fraction = _progress(row.get("progress"))
            if fraction is None:
                problems.append(ImportDiagnostic("E_IMPORT_PROGRESS_INVALID", f"'{row.get('progress')}' is not a progress value",
                                                 row.number, row.columns["progress"], "progress",
                                                 "write 60%, 60 or 0.6 (a value above 1 is a percentage)"))
            else:
                actual["progress"] = fraction
        if actual:
            observations.append({"id": f"{row.get('id')}-observed", "sequence": len(observations) + 1,
                                 "projectObjectId": row.get("id"), "actual": actual})
    return observations, problems


def _actual_yaml(project_id: str, as_of: str | None, observations: list[dict[str, Any]]) -> bytes:
    lines = ["version: chrona/actual-set/v0.3", "kind: actual-set", f"id: {project_id}-observed", "body:"]
    if as_of:
        lines.append(f"  asOf: '{as_of}'")
    lines.append("  observations:")
    for item in observations:
        actual = ", ".join(f"{key}: '{value}'" if isinstance(value, str) else f"{key}: {value}" for key, value in item["actual"].items())
        lines.append(f"    - {{id: {item['id']}, sequence: {item['sequence']}, projectObjectId: {item['projectObjectId']}, actual: {{{actual}}}}}")
    return ("\n".join(lines) + "\n").encode("utf-8")


def _finish(problems: list[ImportDiagnostic], source: str | None) -> tuple[ImportDiagnostic, ...]:
    ordered = sorted(problems, key=lambda item: (item.row or 0, item.column or 0))
    if len(ordered) > ERROR_LIMIT:
        extra = len(ordered) - ERROR_LIMIT
        ordered = ordered[:ERROR_LIMIT] + [ImportDiagnostic("E_IMPORT_TOO_MANY_ERRORS", f"{extra} more errors are not listed")]
    return tuple(ImportDiagnostic(item.code, item.message, item.row, item.column, item.header, item.hint, source, item.source_ref)
                 for item in ordered)
