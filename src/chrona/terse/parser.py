"""Statements of the terse plan syntax (Spec 65 section 3.2) parsed line by line, collecting every error.

The parser knows names and schedule *forms* only. It never computes a date, a cycle or a float, and it repeats no
Core rule (design 3.6, F8).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date

from chrona.terse.diagnostics import SourceRange, TerseDiagnostic, describe, nearest, suggest_name
from chrona.terse.lexer import SourceLine, Token, lex_line, split_lines

VERSION = "0.1"
KINDS = ("task", "gate", "group")
RESERVED = frozenset("terse project calendar task gate group after from until in except work start end at".split())
DAYS = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")
ENDPOINTS = ("start", "end", "at")
# The compiler's name pattern is the `slug` of schemas/common-v0.1.schema.yaml (a test asserts the equality).
SLUG = re.compile(r"[a-z][a-z0-9-]*", re.ASCII)
DATE_SHAPE = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", re.ASCII)
DATE_LIKE = re.compile(r"[0-9]{4}-[0-9]{1,2}-[0-9]{1,2}|[0-9]{1,4}[/.][0-9]{1,2}[/.][0-9]{1,4}", re.ASCII)
AMOUNT = re.compile(r"[1-9][0-9]*(?:d|w|wd)", re.ASCII)
AMOUNT_LIKE = re.compile(r"[0-9]+[a-z]*", re.ASCII)
LAG = re.compile(r"[+-]?(?:0|[1-9][0-9]*)(?:d|w|wd)", re.ASCII)
LAG_LIKE = re.compile(r"[+-]|[+-]?[0-9].*", re.ASCII)


@dataclass(frozen=True)
class Item:
    """A parsed value with the range of the words that spelled it."""

    value: str
    range: SourceRange


@dataclass
class Schedule:
    form: str  # "point" | "span" | "scheduled" | "derived" | "rollup"
    range: SourceRange
    at: str | None = None
    start: str | None = None
    end: str | None = None
    amount: Item | None = None
    anchor: tuple[str, Item] | None = None  # ("start"|"end", date)
    bounds: list[tuple[str, str, Item]] = field(default_factory=list)  # (start|end|at, min|max, date)


@dataclass
class Dep:
    name: Item
    endpoint: Item | None
    lag: Item | None
    lag_calendar: Item | None
    range: SourceRange


@dataclass
class ObjectStatement:
    line: int
    name: Item
    title: Item | None
    kind: Item
    schedule: Schedule
    calendar: Item | None
    calendar_range: SourceRange | None
    deps: list[Dep]
    parent: str | None


@dataclass
class CalendarStatement:
    line: int
    name: Item
    days: list[str]
    days_range: SourceRange
    exceptions: list[tuple[bool, Item]]  # (working, date)
    range: SourceRange


@dataclass
class ProjectStatement:
    line: int
    id: Item
    title: Item | None
    calendar: Item | None


@dataclass
class ParseResult:
    lines: list[str]
    project: ProjectStatement | None
    calendars: list[CalendarStatement]
    objects: list[ObjectStatement]
    problems: list[TerseDiagnostic]
    known_objects: dict[str, int]  # every object name seen (even on a failed line) -> line
    known_calendars: dict[str, int]


class _Stop(Exception):
    """Abandon the current statement; the problem is already recorded by the raiser."""


def valid_date(word: str) -> bool:
    if not DATE_SHAPE.fullmatch(word):
        return False
    try:
        date(int(word[0:4]), int(word[5:7]), int(word[8:10]))
    except ValueError:
        return False
    return True


class _Cursor:
    def __init__(self, line: SourceLine) -> None:
        self.line = line
        self.tokens = line.tokens
        self.index = 0

    def peek(self, offset: int = 0) -> Token | None:
        i = self.index + offset
        return self.tokens[i] if i < len(self.tokens) else None

    def take(self) -> Token:
        token = self.tokens[self.index]
        self.index += 1
        return token

    def at_end(self) -> bool:
        return self.index >= len(self.tokens)

    def end_range(self) -> SourceRange:
        """A one-column range just after the last token, for statements that stop too early."""
        if self.tokens:
            last = self.tokens[-1]
            return SourceRange(last.line, last.end, last.line, last.end + 1)
        return SourceRange(self.line.number, 1, self.line.number, 2)

    def is_word(self, *texts: str) -> bool:
        token = self.peek()
        return token is not None and token.kind == "word" and (not texts or token.text in texts)


class _Parser:
    def __init__(self, text: str) -> None:
        self.lines = split_lines(text)
        self.problems: list[TerseDiagnostic] = []
        self.project: ProjectStatement | None = None
        self.project_line = 0
        self.calendars: list[CalendarStatement] = []
        self.objects: list[ObjectStatement] = []
        self.known_objects: dict[str, int] = {}
        self.known_calendars: dict[str, int] = {}
        self.statements_seen = 0
        self.first_statement_line = 0
        self.terse_seen = False
        self.open_groups: list[tuple[int, str]] = []  # (indent, name)
        self.previous: tuple[int, str, str | None] | None = None  # (indent, name, kind or None when unknown)
        self.misplaced_reported = False

    # -- reporting ---------------------------------------------------------------------------------------------
    def fail(self, code: str, message: str, where: SourceRange, hint: str | None = None) -> _Stop:
        self.problems.append(TerseDiagnostic(code, message, "/", where, hint))
        return _Stop()

    def report(self, code: str, message: str, where: SourceRange, hint: str | None = None) -> None:
        self.problems.append(TerseDiagnostic(code, message, "/", where, hint))

    # -- file --------------------------------------------------------------------------------------------------
    def run(self) -> ParseResult:
        lexed = [lex_line(number, text) for number, text in enumerate(self.lines, 1)]
        self.has_project = any(
            not item.problems and item.tokens and item.tokens[0].kind == "word" and item.tokens[0].text == "project" for item in lexed
        )
        for line in lexed:
            self.problems.extend(line.problems)
            if line.problems:
                self.note_name(line)
                if line.text.lstrip(" ").startswith("project"):
                    self.misplaced_reported = True  # the project line itself failed; do not cascade "project required"
                continue
            if line.tokens:
                self.statement(line)
        if self.project is None and not self.misplaced_reported:
            self.report("E_TERSE_PROJECT_REQUIRED", "the plan has no project statement", SourceRange(1, 1, 1, 2),
                        "start with `project my-plan \"My plan\"`")
        return ParseResult(self.lines, self.project, self.calendars, self.objects, self.problems,
                           self.known_objects, self.known_calendars)

    def note_name(self, line: SourceLine) -> None:
        """A line that failed still registers its name so that later references do not cascade."""
        match = re.match(r" *([^ \",]+)", line.text)
        word = match.group(1) if match else ""
        if SLUG.fullmatch(word) and word not in RESERVED:
            self.known_objects.setdefault(word, line.number)

    def misplaced(self, first: Token) -> None:
        """Report, once, a calendar or object that comes before the project statement."""
        if self.project is None and not self.misplaced_reported:
            self.misplaced_reported = True
            if self.has_project:
                self.report("E_TERSE_DIRECTIVE_ORDER", "the project statement must come before every calendar and object",
                            first.range, "move the `project ...` line to the top (after an optional `terse 0.1`)")
            else:
                self.report("E_TERSE_PROJECT_REQUIRED", "the plan has no project statement", first.range,
                            "start with `project my-plan \"My plan\"`")

    def statement(self, line: SourceLine) -> None:
        cursor = _Cursor(line)
        first = cursor.peek()
        assert first is not None
        directive = first.kind == "word" and first.text in ("terse", "project", "calendar")
        self.statements_seen += 1
        try:
            if line.indent % 2:
                raise self.fail("E_TERSE_INDENT", "indentation must be a multiple of two spaces",
                                SourceRange(line.number, 1, line.number, line.indent + 1),
                                "indent children by exactly two spaces under a group")
            if directive:
                if line.indent:
                    raise self.fail("E_TERSE_INDENT", f"`{first.text}` statements start in column 1",
                                    SourceRange(line.number, 1, line.number, line.indent + 1), "remove the indentation")
                if first.text == "calendar":
                    self.misplaced(first)
                {"terse": self.terse, "project": self.project_statement, "calendar": self.calendar}[first.text](cursor, line)
            else:
                self.misplaced(first)
                self.object(cursor, line)
        except _Stop:
            if first.text == "project" and first.kind == "word":
                self.misplaced_reported = True  # the project line itself failed; do not cascade "project required"
            if not directive:
                self.note_name(line)
                if self.previous is None or self.previous[1] != first.text:
                    # kind unknown: treat the failed line as an open group so its children do not cascade
                    self.previous = (line.indent, first.text, None)
                    while self.open_groups and self.open_groups[-1][0] >= line.indent:
                        self.open_groups.pop()
                    self.open_groups.append((line.indent, first.text))

    # -- helpers -----------------------------------------------------------------------------------------------
    def expect_word(self, cursor: _Cursor, what: str, hint: str | None = None) -> Token:
        token = cursor.peek()
        if token is None:
            raise self.fail("E_TERSE_LINE_INCOMPLETE", f"the statement ends before {what}", cursor.end_range(), hint)
        if token.kind != "word":
            raise self.fail("E_TERSE_TOKEN_UNEXPECTED", f"expected {what}", token.range, hint)
        return cursor.take()

    def check_date(self, token: Token, part: tuple[int, int] | None = None) -> str:
        word = token.text
        where = token.range if part is None else token.part(*part)
        text = word if part is None else word[part[0]:part[1]]
        if valid_date(text):
            return text
        if DATE_SHAPE.fullmatch(text):
            raise self.fail("E_TERSE_DATE_INVALID", f"{text} is not a calendar date", where, "check the month and day")
        raise self.fail("E_TERSE_DATE_INVALID", f"{describe(text)} is not a date; write YYYY-MM-DD with zero padding", where,
                        "for example 2027-03-05")

    def slug_name(self, token: Token, role: str) -> str:
        word = token.text
        if token.kind != "word":
            raise self.fail("E_TERSE_TOKEN_UNEXPECTED", f"expected a {role} name", token.range)
        if word in RESERVED:
            raise self.fail("E_TERSE_NAME_RESERVED", f"`{word}` is a reserved word, not a name", token.range,
                            "choose another name; the reserved words are " + ", ".join(sorted(RESERVED)))
        if not SLUG.fullmatch(word):
            hint = f"try `{suggest_name(word)}`"
            if word.startswith("version:"):
                hint += "; this looks like Project YAML, and compile reads terse plans"
            raise self.fail("E_TERSE_NAME_INVALID",
                            f"{describe(word)} is not a valid name; names are lower-case letters, digits and hyphens, starting with a letter",
                            token.range, hint)
        return word

    def calendar_ref(self, token: Token) -> Item:
        return Item(self.slug_name(token, "calendar"), token.range)

    # -- terse / project ---------------------------------------------------------------------------------------
    def terse(self, cursor: _Cursor, line: SourceLine) -> None:
        keyword = cursor.take()
        if self.statements_seen != 1 or self.terse_seen:
            raise self.fail("E_TERSE_DIRECTIVE_ORDER", "`terse` must be the first statement of the file, once", keyword.range,
                            "move `terse 0.1` to the first line")
        self.terse_seen = True
        version = self.expect_word(cursor, "a version", "write `terse 0.1`")
        if version.text != VERSION:
            raise self.fail("E_TERSE_VERSION_UNSUPPORTED", f"{describe(version.text)} is not a terse version this compiler reads; it reads {VERSION}",
                            version.range, f"write `terse {VERSION}` or update chrona")
        self.finish(cursor)

    def finish(self, cursor: _Cursor, hint: str = "remove it") -> None:
        token = cursor.peek()
        if token is not None:
            if token.kind == "word" and token.text in ("from", "until", "start", "end", "at"):
                hint = "`from`, `until` and `start`/`end` bounds follow a duration, for example `20wd from 2027-03-22`"
                if token.text == "at":
                    hint = "`at >= D` and `at <= D` follow a gate that has no date, for example `launch gate at >= 2027-05-07 after qa +2wd`"
            raise self.fail("E_TERSE_TOKEN_UNEXPECTED", f"unexpected {describe(token.text)}", token.range, hint)

    def project_statement(self, cursor: _Cursor, line: SourceLine) -> None:
        keyword = cursor.take()
        if self.project is not None:
            raise self.fail("E_TERSE_DIRECTIVE_ORDER", f"the project is already declared on line {self.project_line}", keyword.range,
                            "a plan has exactly one project statement")
        token = self.expect_word(cursor, "a project id", "write `project my-plan \"My plan\"`")
        if token.text in RESERVED:
            raise self.fail("E_TERSE_NAME_RESERVED", f"`{token.text}` is a reserved word, not a project id", token.range,
                            "choose another id")
        title = None
        calendar = None
        if cursor.peek() is not None and cursor.peek().kind == "string":
            title = self.title(cursor.take())
        if cursor.is_word("calendar"):
            cursor.take()
            calendar = self.calendar_ref(self.expect_word(cursor, "a calendar name"))
        self.finish(cursor)
        self.project = ProjectStatement(line.number, Item(token.text, token.range), title, calendar)
        self.project_line = line.number

    def title(self, token: Token) -> Item:
        if token.text == "":
            raise self.fail("E_TERSE_TITLE_EMPTY", "a title may not be empty", token.range, "write a title or omit the string")
        return Item(token.text, token.range)

    # -- calendars ---------------------------------------------------------------------------------------------
    def calendar(self, cursor: _Cursor, line: SourceLine) -> None:
        keyword = cursor.take()
        name_token = self.expect_word(cursor, "a calendar name", "write `calendar standard mon-fri`")
        name = self.slug_name(name_token, "calendar")
        if name in self.known_calendars:
            raise self.fail("E_TERSE_NAME_DUPLICATE", f"calendar '{name}' is already defined on line {self.known_calendars[name]}",
                            name_token.range, "calendar names are unique")
        self.known_calendars[name] = line.number
        days, days_range = self.days(cursor)
        exceptions: list[tuple[bool, Item]] = []
        seen: dict[str, Token] = {}
        while not cursor.at_end():
            token = cursor.take()
            if token.kind != "word" or token.text not in ("except", "work"):
                raise self.fail("E_TERSE_TOKEN_UNEXPECTED", f"expected `except` or `work`, found {describe(token.text)}", token.range,
                                "list non-working dates after `except` and extra working dates after `work`")
            if token.text in seen:
                raise self.fail("E_TERSE_CLAUSE_DUPLICATE", f"`{token.text}` is given twice for calendar '{name}'", token.range,
                                f"put every date after one `{token.text}`")
            seen[token.text] = token
            count = 0
            while not cursor.at_end():
                nxt = cursor.peek()
                if nxt.kind == "word" and nxt.text in ("except", "work"):
                    break
                if nxt.kind == "comma":
                    if count == 0:
                        raise self.fail("E_TERSE_TOKEN_UNEXPECTED", "a date must follow the keyword before a comma", nxt.range)
                    cursor.take()
                    if cursor.at_end() or cursor.peek().kind != "word" or cursor.peek().text in ("except", "work"):
                        raise self.fail("E_TERSE_LINE_INCOMPLETE", "a comma must be followed by a date", cursor.end_range())
                    continue
                if nxt.kind != "word":
                    raise self.fail("E_TERSE_TOKEN_UNEXPECTED", "expected a date", nxt.range)
                cursor.take()
                if ".." in nxt.text:
                    raise self.fail("E_TERSE_UNSUPPORTED", "a date range is not supported here; one date is one exception", nxt.range,
                                    "list each date: `except 2027-04-02 2027-04-03`")
                exceptions.append((token.text == "work", Item(self.check_date(nxt), nxt.range)))
                count += 1
            if count == 0:
                raise self.fail("E_TERSE_LINE_INCOMPLETE", f"`{token.text}` needs at least one date", token.range,
                                f"write `{token.text} 2027-04-02`")
        self.calendars.append(CalendarStatement(line.number, Item(name, name_token.range), days, days_range, exceptions,
                                                keyword.range.through(cursor.tokens[-1].range)))

    def days(self, cursor: _Cursor) -> tuple[list[str], SourceRange]:
        first = self.expect_word(cursor, "the working days", "write `mon-fri` or `mon-wed,fri`")
        chosen: list[str] = []
        last = first
        token: Token | None = first
        while True:
            assert token is not None
            for day in self.day_item(token):
                if day in chosen:
                    raise self.fail("E_TERSE_DAYS_INVALID", f"{day} is listed twice", token.range, "list each weekday once")
                chosen.append(day)
            last = token
            if cursor.peek() is not None and cursor.peek().kind == "comma":
                cursor.take()
                token = self.expect_word(cursor, "a weekday after the comma")
                continue
            break
        return [d for d in DAYS if d in chosen], first.range.through(last.range)

    def day_item(self, token: Token) -> list[str]:
        parts = token.text.split("-")
        if not all(part in DAYS for part in parts) or len(parts) > 2:
            raise self.fail("E_TERSE_DAYS_INVALID", f"{describe(token.text)} is not a weekday or weekday range; use mon tue wed thu fri sat sun",
                            token.range, "write `mon-fri` or `mon-wed,fri`")
        if len(parts) == 1:
            return parts
        a, b = DAYS.index(parts[0]), DAYS.index(parts[1])
        if a >= b:
            raise self.fail("E_TERSE_DAYS_INVALID", f"{token.text} is not an increasing range within mon..sun", token.range,
                            "list the days instead, for example `fri,sat,sun,mon`" if a > b else f"write `{parts[0]}`")
        return list(DAYS[a:b + 1])

    # -- objects -----------------------------------------------------------------------------------------------
    def object(self, cursor: _Cursor, line: SourceLine) -> None:
        first = cursor.take()
        name = first.text
        if first.kind != "word":
            raise self.fail("E_TERSE_TOKEN_UNEXPECTED", "a line starts with an object name, a project, a calendar or terse", first.range)
        if name in KINDS:
            second = cursor.peek()
            hint = f"write the name first: `{second.text} {name} ...`" if second is not None and second.kind == "word" else "write the name first"
            raise self.fail("E_TERSE_NAME_RESERVED", f"`{name}` is a kind, not a name; write the name first", first.range, hint)
        slug_name = self.slug_name(first, "object")
        if slug_name in self.known_objects:
            raise self.fail("E_TERSE_NAME_DUPLICATE", f"'{name}' is already defined on line {self.known_objects[name]}", first.range,
                            "object names are unique; choose another")
        self.known_objects[name] = line.number
        parent = self.place(line, name)
        title: Item | None = None
        token = cursor.peek()
        if token is None:
            raise self.fail("E_TERSE_LINE_INCOMPLETE", f"'{name}' needs a kind: task, gate or group", cursor.end_range(),
                            f"write `{name} task 5d`")
        if token.kind == "string":
            title = self.title(cursor.take())
        elif token.kind == "word" and token.text not in KINDS:
            later_kind = [t for t in cursor.tokens[cursor.index + 1:] if t.kind == "word" and t.text in KINDS]
            if later_kind:
                raise self.fail("E_TERSE_TITLE_UNQUOTED", "a title needs double quotes (a title with spaces always does)", token.range,
                                f"write {name} \"Your title\" {later_kind[0].text} ...")
        kind_token = cursor.peek()
        if kind_token is None:
            raise self.fail("E_TERSE_LINE_INCOMPLETE", f"'{name}' needs a kind: task, gate or group", cursor.end_range(),
                            f"write `{name} task 5d`")
        if kind_token.kind != "word" or kind_token.text not in KINDS:
            close = nearest(kind_token.text, KINDS) if kind_token.kind == "word" else None
            hint = f"did you mean `{close}`?" if close else "write task, gate or group"
            raise self.fail("E_TERSE_KIND_UNKNOWN",
                            f"unknown kind {describe(kind_token.text)}; known: {', '.join(KINDS)} (other types are written in YAML)",
                            kind_token.range, hint)
        cursor.take()
        kind = kind_token.text
        self.previous = (line.indent, name, kind)
        if kind == "group":
            self.open_groups.append((line.indent, name))
            leftover = cursor.peek()
            if leftover is not None:
                what = {"after": "a group takes no `after`; it may be a predecessor", "calendar": "a group takes no calendar"}.get(
                    leftover.text, "a group takes no schedule; its dates come from its children")
                raise self.fail("E_TERSE_TOKEN_UNEXPECTED", what, leftover.range, "remove it")
            schedule = Schedule("rollup", kind_token.range)
            calendar = None
            calendar_range = None
            deps: list[Dep] = []
        else:
            schedule = self.schedule(cursor, name, kind, kind_token)
            calendar = None
            calendar_range = None
            if cursor.is_word("calendar"):
                keyword = cursor.take()
                calendar = self.calendar_ref(self.expect_word(cursor, "a calendar name"))
                calendar_range = keyword.range.through(calendar.range)
            deps = self.after(cursor) if cursor.is_word("after") else []
            self.finish(cursor, "separate dependencies with a comma" if deps else "remove it")
        self.objects.append(ObjectStatement(line.number, Item(name, first.range), title, Item(kind, kind_token.range),
                                            schedule, calendar, calendar_range, deps, parent))

    def place(self, line: SourceLine, name: str) -> str | None:
        """S2: the parent of this line from its indentation. Raises through `fail` for an impossible indent."""
        indent = line.indent
        where = SourceRange(line.number, 1, line.number, max(indent, 1) + 1)
        while self.open_groups and self.open_groups[-1][0] >= indent:
            self.open_groups.pop()
        if indent == 0:
            return None
        if self.open_groups and self.open_groups[-1][0] == indent - 2:
            return self.open_groups[-1][1]
        previous = self.previous
        if previous is not None and previous[0] == indent - 2 and previous[2] not in (None, "group"):
            raise self.fail("E_TERSE_CHILDREN_NOT_ALLOWED", f"'{previous[1]}' is not a group, so it cannot have children", where,
                            f"make '{previous[1]}' a group or remove the indentation")
        raise self.fail("E_TERSE_INDENT", "this indentation does not match an open group", where,
                        "indent a child exactly two spaces deeper than its group, directly below it")

    def derived(self, cursor: _Cursor, name: str, kind_token: Token) -> Schedule:
        """A gate with no date: its date is derived from its `after` clause (T1), optionally with `at >= D` / `at <= D` (T2)."""
        has_after = any(t.kind == "word" and t.text == "after" for t in cursor.tokens[cursor.index:])
        bounds: list[tuple[str, str, Item]] = []
        seen: set[str] = set()
        while cursor.is_word("at"):
            keyword = cursor.take()
            op = self.expect_word(cursor, "`>=` or `<=`", "write `at >= 2027-05-07` for a floor or `at <= 2027-06-30` for a cap")
            if op.text not in (">=", "<="):
                raise self.fail("E_TERSE_TOKEN_UNEXPECTED", f"expected `>=` or `<=` after `at`, found {describe(op.text)}", op.range,
                                "write `at >= D` for a minimum or `at <= D` for a maximum")
            if op.text in seen:
                raise self.fail("E_TERSE_CLAUSE_DUPLICATE", f"`at {op.text}` is given twice", keyword.range, "keep one")
            seen.add(op.text)
            date_token = self.expect_word(cursor, "a date", f"write `at {op.text} 2027-05-07`")
            bounds.append(("at", "min" if op.text == ">=" else "max",
                           Item(self.check_date(date_token), keyword.range.through(date_token.range))))
        if not has_after:
            if bounds:
                raise self.fail("E_TERSE_SCHEDULE_REQUIRED", f"'{name}' has a bound but no `after` to derive its date from",
                                bounds[0][2].range,
                                f"a floor alone is a fixed date: write `{name} gate DATE`, or add `after X` to derive the date")
            where = cursor.peek().range if cursor.peek() is not None else cursor.end_range()
            raise self.fail("E_TERSE_SCHEDULE_REQUIRED", f"'{name}' has no schedule", where,
                            f"a gate needs a date, or `after X` to derive one, for example `{name} gate 2027-03-05` "
                            f"or `{name} gate after other +2wd`")
        where = kind_token.range if not bounds else bounds[0][2].range.through(bounds[-1][2].range)
        return Schedule("derived", where, bounds=bounds)

    def schedule(self, cursor: _Cursor, name: str, kind: str, kind_token: Token) -> Schedule:
        token = cursor.peek()
        if kind == "gate" and (token is None or (token.kind == "word" and token.text in ("after", "calendar", "at"))):
            return self.derived(cursor, name, kind_token)
        if token is None or (token.kind == "word" and token.text in ("after", "calendar")):
            where = token.range if token is not None else cursor.end_range()
            raise self.fail("E_TERSE_SCHEDULE_REQUIRED", f"'{name}' has no schedule", where,
                            f"a task needs a duration (`5d`) or `D..D`, for example `{name} task 5d` or "
                            f"`{name} task 2027-03-01..2027-03-08`")
        if token.kind != "word":
            raise self.fail("E_TERSE_TOKEN_UNEXPECTED", "expected a date, a date range or a duration", token.range)
        cursor.take()
        word = token.text
        following = cursor.peek()
        if ".." in word:
            parts = word.split("..")
            if len(parts) != 2 or not parts[0] or not parts[1]:
                raise self.fail("E_TERSE_TOKEN_UNEXPECTED", "no spaces around `..`; write a span as D1..D2", token.range,
                                "for example 2026-10-01..2026-10-31")
            start = self.check_date(token, (0, len(parts[0])))
            end = self.check_date(token, (len(parts[0]) + 2, len(word)))
            return Schedule("span", token.range, start=start, end=end)
        if following is not None and following.kind == "word" and following.text.startswith("..") and valid_date(word):
            raise self.fail("E_TERSE_TOKEN_UNEXPECTED", "no spaces around `..`; write a span as D1..D2", following.range,
                            "for example 2026-10-01..2026-10-31")
        if DATE_SHAPE.fullmatch(word) or DATE_LIKE.fullmatch(word):
            return Schedule("point", token.range, at=self.check_date(token))
        if not AMOUNT.fullmatch(word):
            spelled = word.isdigit() and following is not None and following.kind == "word" and following.text.isalpha()
            where = token.range.through(following.range) if spelled else token.range
            shown = f"{word} {following.text}" if spelled else word
            reason = "is not a duration" if spelled or not word.isdigit() else "has no unit"
            raise self.fail("E_TERSE_AMOUNT_INVALID",
                            f"{describe(shown)} {reason}; write 20d (calendar days), 20w (weeks) or 20wd (working days)", where,
                            "write 20d for calendar days; 20wd needs a `calendar` statement" if AMOUNT_LIKE.fullmatch(word) else
                            "a date is YYYY-MM-DD, a duration is a whole number with d, w or wd")
        schedule = Schedule("scheduled", token.range, amount=Item(word, token.range))
        seen: set[str] = set()
        while cursor.is_word("from", "until", "start", "end"):
            keyword = cursor.take()
            if keyword.text in ("from", "until"):
                if "anchor" in seen:
                    raise self.fail("E_TERSE_CLAUSE_DUPLICATE", "a schedule has at most one anchor (`from` or `until`)", keyword.range,
                                    "keep one of them")
                seen.add("anchor")
                date_token = self.expect_word(cursor, "a date", f"write `{keyword.text} 2027-03-22`")
                schedule.anchor = ("start" if keyword.text == "from" else "end",
                                   Item(self.check_date(date_token), keyword.range.through(date_token.range)))
            else:
                op = self.expect_word(cursor, "`>=` or `<=`", f"write `{keyword.text} <= 2027-09-08`")
                if op.text not in (">=", "<="):
                    raise self.fail("E_TERSE_TOKEN_UNEXPECTED", f"expected `>=` or `<=` after `{keyword.text}`, found {describe(op.text)}", op.range,
                                    f"write `{keyword.text} >= D` for a minimum or `{keyword.text} <= D` for a maximum")
                key = f"{keyword.text}{op.text}"
                if key in seen:
                    raise self.fail("E_TERSE_CLAUSE_DUPLICATE", f"`{keyword.text} {op.text}` is given twice", keyword.range, "keep one")
                seen.add(key)
                date_token = self.expect_word(cursor, "a date", f"write `{keyword.text} {op.text} 2027-09-08`")
                schedule.bounds.append((keyword.text, "min" if op.text == ">=" else "max",
                                        Item(self.check_date(date_token), keyword.range.through(date_token.range))))
        schedule.range = token.range.through(cursor.tokens[cursor.index - 1].range)
        return schedule

    def after(self, cursor: _Cursor) -> list[Dep]:
        keyword = cursor.take()
        deps: list[Dep] = []
        while True:
            token = cursor.peek()
            if token is None:
                raise self.fail("E_TERSE_LINE_INCOMPLETE", "`after` needs an object to follow", cursor.end_range(),
                                "write `after other-object` or `after other-object +1wd`")
            if token.kind != "word":
                raise self.fail("E_TERSE_TOKEN_UNEXPECTED", "expected the name of the object this one follows", token.range)
            cursor.take()
            ref, _, endpoint = token.text.partition(".")
            ref_item = Item(ref, token.part(0, len(ref)))
            if not SLUG.fullmatch(ref) or ref in RESERVED:
                raise self.fail("E_TERSE_REFERENCE_UNKNOWN",
                                f"no object can be named {describe(ref)}" if ref else f"{describe(token.text)} does not start with an object name",
                                ref_item.range,
                                f"`after` names an object defined in this plan; try `{suggest_name(ref)}`" if ref else None)
            endpoint_item = None
            if "." in token.text:
                if endpoint not in ENDPOINTS:
                    raise self.fail("E_TERSE_REFERENCE_UNKNOWN", f"unknown endpoint {describe(endpoint)}; use .start, .end or .at",
                                    token.part(len(ref) + 1, len(token.text)), "for example `after design.start`")
                endpoint_item = Item(endpoint, token.part(len(ref) + 1, len(token.text)))
            lag = lag_calendar = None
            last = token
            nxt = cursor.peek()
            if nxt is not None and nxt.kind == "word" and nxt.text not in ("in",) and LAG_LIKE.fullmatch(nxt.text):
                cursor.take()
                if not LAG.fullmatch(nxt.text):
                    hint = "attach the sign: `+1wd`" if nxt.text in ("+", "-") else "a lag is a signed whole number with d, w or wd, for example +1wd or -2d"
                    raise self.fail("E_TERSE_LAG_INVALID", f"{describe(nxt.text)} is not a lag", nxt.range, hint)
                lag = Item(nxt.text[1:] if nxt.text.startswith("+") else nxt.text, nxt.range)
                last = nxt
                if cursor.is_word("in"):
                    cursor.take()
                    cal = self.calendar_ref(self.expect_word(cursor, "a calendar name", "write `+1wd in range`"))
                    lag_calendar = cal
                    last = cursor.tokens[cursor.index - 1]
            elif cursor.is_word("in"):
                raise self.fail("E_TERSE_TOKEN_UNEXPECTED", "`in CAL` follows a lag", cursor.peek().range,
                                "write `after other +1wd in calendar-name`")
            deps.append(Dep(ref_item, endpoint_item, lag, lag_calendar, token.range.through(last.range)))
            if cursor.peek() is not None and cursor.peek().kind == "comma":
                cursor.take()
                continue
            break
        return deps


def parse(text: str) -> ParseResult:
    return _Parser(text).run()
