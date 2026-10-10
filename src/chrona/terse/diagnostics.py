"""Positioned diagnostics, the stable code catalogue and hint helpers of the terse plan syntax (Spec 65)."""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Mapping

from chrona.core.diagnostics import Diagnostic
from chrona.core.suggestions import distance, nearest  # noqa: F401  (the one nearest-name rule, shared with Project validation)

# Compiler-owned codes (Spec 65 section 7). Every code here has a negative fixture; a test fails both ways.
CODES: Mapping[str, str] = {
    "E_TERSE_ENCODING": "the input is not valid UTF-8",
    "E_TERSE_TAB": "a tab character",
    "E_TERSE_CONTROL_CHARACTER": "a control character other than a tab, or a lone carriage return",
    "E_TERSE_STRING_UNTERMINATED": "a string has no closing quote",
    "E_TERSE_STRING_ESCAPE": "a string escape other than \\\" and \\\\",
    "E_TERSE_TITLE_EMPTY": "an empty title",
    "E_TERSE_INDENT": "an odd, too deep or parentless indentation",
    "E_TERSE_CHILDREN_NOT_ALLOWED": "a child under an object that is not a group",
    "E_TERSE_TOKEN_UNEXPECTED": "a token that the grammar does not allow here",
    "E_TERSE_LINE_INCOMPLETE": "a statement that ends before it is complete",
    "E_TERSE_TITLE_UNQUOTED": "a multi-word title without quotes",
    "E_TERSE_PROJECT_REQUIRED": "the plan has no project statement",
    "E_TERSE_DIRECTIVE_ORDER": "a project, terse or calendar statement in the wrong place",
    "E_TERSE_VERSION_UNSUPPORTED": "a terse version this compiler does not read",
    "E_TERSE_UNSUPPORTED": "a recognised construct this compiler release does not implement",
    "E_TERSE_TOO_MANY_ERRORS": "more than 50 errors; the rest are not listed",
    "E_TERSE_NAME_INVALID": "a name that is not a slug",
    "E_TERSE_NAME_RESERVED": "a reserved word used as a name",
    "E_TERSE_NAME_DUPLICATE": "a name defined twice in one namespace",
    "E_TERSE_KIND_UNKNOWN": "an object kind other than task, gate or group",
    "E_TERSE_REFERENCE_UNKNOWN": "a dependency that names no object",
    "E_TERSE_CALENDAR_UNKNOWN": "a calendar name that is not declared",
    "E_TERSE_DATE_INVALID": "a date that is not a real YYYY-MM-DD date",
    "E_TERSE_AMOUNT_INVALID": "a duration that is not a positive d, w or wd amount",
    "E_TERSE_LAG_INVALID": "a lag that is not a signed d, w or wd amount",
    "E_TERSE_DAYS_INVALID": "a weekday list that is not an increasing set of weekdays",
    "E_TERSE_SCHEDULE_REQUIRED": "a task or gate without a schedule",
    "E_TERSE_CLAUSE_DUPLICATE": "a clause given twice",
    "E_TERSE_OUTPUT_EXISTS": "the output file already exists",
    "E_TERSE_INPUT_IO": "the plan could not be read",
    "E_TERSE_COMPILER_DEFECT": "the compiled Project failed structural validation",
}

# Reserved for a later release (design 5.2); not produced by this compiler.
RESERVED_CODES: tuple[str, ...] = ("E_TERSE_OVERLAY_CONFLICT", "E_TERSE_OVERLAY_UNKNOWN_OBJECT")


@dataclass(frozen=True)
class SourceRange:
    """A span of one line: 1-based code points, the end column exclusive."""

    line: int
    column: int
    end_line: int
    end_column: int

    def as_dict(self) -> dict[str, int]:
        return {"line": self.line, "column": self.column, "endLine": self.end_line, "endColumn": self.end_column}

    def through(self, other: "SourceRange") -> "SourceRange":
        """The span from this range's start to the other's end."""
        return SourceRange(self.line, self.column, other.end_line, other.end_column)


@dataclass(frozen=True)
class TerseDiagnostic(Diagnostic):
    """A Core diagnostic (`id`, `message`, `path` as the pointer) plus a source position and a hint."""

    range: SourceRange | None = None
    hint: str | None = None
    source: str | None = None
    component: str = "terse"

    @property
    def code(self) -> str:
        return self.id

    def with_source(self, source: str | None) -> "TerseDiagnostic":
        return TerseDiagnostic(self.id, self.message, self.path, self.range, self.hint, source, self.component,
                               details=self.details)

    def as_dict(self) -> dict[str, Any]:
        """The CLI diagnostic shape of design 7.1."""
        payload: dict[str, Any] = {
            "code": self.id, "severity": "error", "component": self.component,
            "sourceRef": self.path or "/", "revisionRefs": [], "message": self.message,
        }
        if self.details is not None:
            payload["details"] = self.details
        if self.source is not None:
            payload["source"] = self.source
        if self.range is not None:
            payload["sourceRange"] = self.range.as_dict()
        if self.hint is not None:
            payload["hint"] = self.hint
        return payload


def suggest_name(word: str) -> str:
    """A conforming slug for the hint only: lower-cased, runs of other characters become one hyphen."""
    text = re.sub(r"[^a-z0-9]+", "-", word.lower()).strip("-")
    if not text:
        return "name"
    return text if text[0].isalpha() else "n-" + text


def describe(word: str) -> str:
    """Quote a word for a message; name the code points that are not plain printable ASCII."""
    if word.isascii() and word.isprintable():
        return f"'{word}'"
    odd = " ".join(f"U+{ord(c):04X}" for c in word if not (c.isascii() and c.isprintable()))
    return f"'{word}' ({odd})"
