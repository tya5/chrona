"""Lexical rules L1-L7 of the terse plan syntax: text to lines, a line to tokens. No I/O."""
from __future__ import annotations

from dataclasses import dataclass

from chrona.terse.diagnostics import SourceRange, TerseDiagnostic, describe


@dataclass(frozen=True)
class Token:
    kind: str  # "word" | "string" | "comma"
    text: str  # a string token holds the decoded value
    line: int
    column: int
    end: int  # exclusive

    @property
    def range(self) -> SourceRange:
        return SourceRange(self.line, self.column, self.line, self.end)

    def part(self, start: int, stop: int) -> SourceRange:
        """The range of text[start:stop] of a word token."""
        return SourceRange(self.line, self.column + start, self.line, self.column + max(stop, start + 1))


@dataclass
class SourceLine:
    number: int
    text: str
    indent: int
    tokens: list[Token]
    problems: list[TerseDiagnostic]


def decode(data: bytes) -> tuple[str | None, TerseDiagnostic | None]:
    """L1: strict UTF-8 with an optional BOM; the finding is positioned at the first bad byte."""
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as error:
        before = data[:error.start].decode("utf-8", errors="replace")
        line = before.count("\n") + 1
        column = len(before.rsplit("\n", 1)[-1].lstrip("\ufeff")) + 1
        return None, TerseDiagnostic(
            "E_TERSE_ENCODING", f"the plan is not valid UTF-8 (byte offset {error.start})", "/",
            SourceRange(line, column, line, column + 1), "save the file as UTF-8")
    return text, None


def split_lines(text: str) -> list[str]:
    """L2: LF or CRLF separate lines, a final newline is optional, a BOM is ignored."""
    if text.startswith("\ufeff"):
        text = text[1:]
    lines = text.replace("\r\n", "\n").split("\n")
    if len(lines) > 1 and lines[-1] == "":
        lines.pop()
    return lines


def _problem(code: str, message: str, number: int, column: int, end: int, hint: str | None = None) -> TerseDiagnostic:
    return TerseDiagnostic(code, message, "/", SourceRange(number, column, number, max(end, column + 1)), hint)


def lex_line(number: int, text: str) -> SourceLine:
    """L3-L7. A control character stops the line; a string error stops the line at that string."""
    indent = len(text) - len(text.lstrip(" "))
    problems: list[TerseDiagnostic] = []
    for position, char in enumerate(text, 1):
        code_point = ord(char)
        if code_point < 0x20 or code_point == 0x7F:
            if char == "\t":
                problems.append(_problem("E_TERSE_TAB", "a tab character; indent and separate with spaces", number, position, position + 1,
                                         "replace the tab with spaces"))
            else:
                what = "a lone carriage return" if char == "\r" else f"control character U+{code_point:04X}"
                problems.append(_problem("E_TERSE_CONTROL_CHARACTER", f"{what} is not allowed", number, position, position + 1,
                                         "remove it"))
            return SourceLine(number, text, indent, [], problems)

    tokens: list[Token] = []
    length = len(text)
    i = indent
    previous_end = -1  # end index of the previous word or string, to catch missing separators
    while i < length:
        char = text[i]
        if char == " ":
            i += 1
        elif char == "#":
            break
        elif char == ",":
            tokens.append(Token("comma", ",", number, i + 1, i + 2))
            i += 1
        elif char == '"':
            if previous_end == i:
                problems.append(_problem("E_TERSE_TOKEN_UNEXPECTED", "a string must be separated from the previous word by a space",
                                         number, i + 1, i + 2, "write a space before the opening quote"))
                break
            j, buffer = i + 1, []
            while True:
                if j >= length:
                    problems.append(_problem("E_TERSE_STRING_UNTERMINATED", "this string has no closing quote", number, i + 1, i + 2,
                                             "close the title with a \" on the same line"))
                    return SourceLine(number, text, indent, tokens, problems)
                if text[j] == "\\":
                    if j + 1 < length and text[j + 1] in '"\\':
                        buffer.append(text[j + 1])
                        j += 2
                        continue
                    problems.append(_problem("E_TERSE_STRING_ESCAPE", "only \\\" and \\\\ are escapes inside a string", number, j + 1, j + 3,
                                             "write \\\\ for a backslash and \\\" for a quote"))
                    return SourceLine(number, text, indent, tokens, problems)
                if text[j] == '"':
                    break
                buffer.append(text[j])
                j += 1
            tokens.append(Token("string", "".join(buffer), number, i + 1, j + 2))
            i = j + 1
            previous_end = i
            if i < length and text[i] not in ' ,':
                problems.append(_problem("E_TERSE_TOKEN_UNEXPECTED", "a string must be followed by a space", number, i + 1, i + 2,
                                         "write a space after the closing quote"))
                break
        else:
            j = i
            while j < length and text[j] not in ' ",':
                j += 1
            tokens.append(Token("word", text[i:j], number, i + 1, j + 1))
            i = j
            previous_end = i
    return SourceLine(number, text, indent, tokens, problems)


def word_note(word: str) -> str:
    """How a message quotes a word; names the code point of an odd character (L3)."""
    return describe(word)
