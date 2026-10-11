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

from chrona.usecases.terse_compile import compile_plan, emit_project_text

COLUMNS = ("id", "title", "type", "start", "end", "finish", "duration", "parent", "predecessors", "deadline", "calendar",
           "progress", "actual_start", "actual_finish")
"""The closed column vocabulary. Headers match case-insensitively; spaces and hyphens read as underscores."""

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

    def as_dict(self) -> dict[str, Any]:
        where = f" (row {self.row}, column {self.column} `{self.header}`)" if self.row and self.column else (
            f" (row {self.row})" if self.row else "")
        record: dict[str, Any] = {"code": self.code, "severity": "error", "component": "import", "sourceRef": "/",
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


def slug(text: str, fallback: str = "plan") -> str:
    """A project id from free text: lower-case letters, digits and hyphens, starting with a letter."""
    value = _SLUG.sub("-", text.lower()).strip("-") or fallback
    return value if value[0].isalpha() else f"{fallback}-{value}"


def _canonical(header: str, mapping: Mapping[str, str]) -> str | None:
    key = re.sub(r"[\s-]+", "_", header.strip().lower())
    key = mapping.get(header.strip(), mapping.get(key, key))
    return key if key in COLUMNS else None


def read_table(text: str, delimiter: str, mapping: Mapping[str, str] | None = None
               ) -> tuple[list[_Row], list[ImportDiagnostic], list[str]]:
    """Rows keyed by canonical column name; unknown headers are kept as `fields`."""
    mapping = mapping or {}
    problems: list[ImportDiagnostic] = []
    reader = csv.reader(io.StringIO(text.lstrip("﻿"), newline=""), delimiter=delimiter)
    rows = [(reader.line_num, record) for record in reader]
    if not rows:
        return [], [ImportDiagnostic("E_IMPORT_EMPTY", "the table is empty", hint="start with a header row such as `id,title,type,start,end`")], []
    header_number, headers = rows[0]
    header_number = 1
    columns: dict[str, int] = {}
    extra: dict[int, str] = {}
    for index, header in enumerate(headers, start=1):
        name = _canonical(header, mapping)
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
    return parsed, problems, [name for name in COLUMNS if name in columns]


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
                 as_of: str | None = None, mapping: Mapping[str, str] | None = None, source: str | None = None) -> ImportResult:
    """Convert a table to Project YAML (and an Actual Set when it has actual columns). Reports every row error in one run."""
    rows, problems, _present = read_table(text, delimiter, mapping)
    if "E_IMPORT_COLUMN_MISSING" in {item.code for item in problems} or "E_IMPORT_EMPTY" in {item.code for item in problems}:
        return ImportResult(None, None, _finish(problems, source))
    preface = ["terse 0.1", f"project {project_id} {_quote(title or project_id)}", *[f"calendar {item}" for item in calendars]]
    ordered = _order(rows, problems)
    plan = _generate(ordered, preface)
    compiled = compile_plan("\n".join(plan.lines).encode("utf-8") + b"\n", source)
    for item in compiled.diagnostics:
        line = item.range.line if item.range is not None else None
        column = item.range.column if item.range is not None else None
        row, index, header = _locate(plan, line, column, item.id)
        message = item.message
        if row is None and item.range is not None and item.range.line <= len(preface):
            message = f"{message} (the generated project or calendar line)"
        problems.append(ImportDiagnostic(item.id, message, row, index, header, item.hint, source))
    if problems:
        return ImportResult(None, None, _finish(problems, source))
    project = compiled.project
    assert project is not None
    objects = project.get("objects", {})
    for row, _depth in ordered:
        if row.fields:
            objects[row.get("id")]["fields"] = dict(row.fields)
    observations, actual_problems = _observations(ordered)
    problems.extend(actual_problems)
    if as_of is not None and not _valid_date(as_of):
        problems.append(ImportDiagnostic("E_IMPORT_AS_OF_INVALID", f"--as-of '{as_of}' is not a YYYY-MM-DD date"))
    if problems:
        return ImportResult(None, None, _finish(problems, source))
    project_yaml = emit_project_text(project).encode("utf-8")
    actual_yaml = _actual_yaml(project_id, as_of, observations) if observations else None
    return ImportResult(project_yaml, actual_yaml, ())


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
                actual.setdefault(key, value)
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
    return tuple(ImportDiagnostic(item.code, item.message, item.row, item.column, item.header, item.hint, source) for item in ordered)
