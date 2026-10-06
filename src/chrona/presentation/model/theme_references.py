"""Ingress-only resolution of Theme number-token references and simple expressions (#1151).

A `number` token of `body.values` may be written as a reference `{ref: <token>}` or as a closed arithmetic
expression `{expr: "2 * {spacing.m} + 1"}`. Resolution happens once, at Theme load, before the Theme is parsed as a
contract: the resolved Theme is an ordinary plain-number Theme, so identity, Layout, Scene and adapters never see a
reference. A Theme that uses no reference is returned unchanged (the very same object).

Expression grammar (no functions, no units, no free evaluation):

    expr    := term (("+" | "-") term)*
    term    := unary (("*" | "/") unary)*
    unary   := "-" unary | primary
    primary := NUMBER | "{" token-name "}" | "(" expr ")"

Arithmetic is exact `Decimal` arithmetic over `Decimal(str(number))`, the rule every Theme number follows when Layout
reads it, with a fixed local context (28 significant digits, half-even), so the result does not depend on the
platform. An integral result is written as an `int`, any other as the shortest round-trip `float`.
"""
from __future__ import annotations

from copy import deepcopy
from decimal import Context, Decimal, DivisionByZero, InvalidOperation, ROUND_HALF_EVEN
import re
from typing import Any, Mapping


_CONTEXT = Context(prec=28, rounding=ROUND_HALF_EVEN, traps=[InvalidOperation, DivisionByZero])
_MAX_EXPRESSION = 256
_MAX_DEPTH = 16
_TOKEN = re.compile(r"\s*(?:(?P<number>\d+(?:\.\d+)?)|(?P<ref>\{[^{}]+\})|(?P<op>[-+*/()]))")


class ThemeReferenceError(ValueError):
    def __init__(self, code: str, pointer: str, detail: str):
        super().__init__(code)
        self.code = code
        self.pointer = pointer
        self.detail = detail


def _escape(name: str) -> str:
    return name.replace("~", "~0").replace("/", "~1")


def _source(entry: Any) -> tuple[str, Any] | None:
    """`("ref"|"expr", text)` when the token value is a reference form, else None."""
    value = entry.get("value") if isinstance(entry, Mapping) else None
    if isinstance(value, Mapping) and len(value) == 1:
        for key in ("ref", "expr"):
            if key in value:
                return key, value[key]
    return None


def uses_references(theme: Mapping[str, Any]) -> bool:
    body = theme.get("body") if isinstance(theme, Mapping) else None
    values = body.get("values") if isinstance(body, Mapping) else None
    return isinstance(values, Mapping) and any(_source(entry) is not None for entry in values.values())


def _parse(text: str, pointer: str) -> tuple:
    """Parse into a tree: ("n", Decimal) | ("r", name) | ("neg", t) | (op, left, right)."""
    if len(text) > _MAX_EXPRESSION:
        raise ThemeReferenceError("E_THEME_REF_SYNTAX", pointer, f"the expression is longer than {_MAX_EXPRESSION} characters")
    tokens: list[tuple[str, str]] = []
    position = 0
    while text[position:].strip():
        match = _TOKEN.match(text, position)
        if match is None:
            raise ThemeReferenceError("E_THEME_REF_SYNTAX", pointer, f"unexpected character at offset {position + len(text[position:]) - len(text[position:].lstrip())}: {text[position:].lstrip()[:1]!r}")
        kind = match.lastgroup
        tokens.append((kind, match.group(kind)))
        position = match.end()
    cursor = 0

    def peek() -> tuple[str, str] | None:
        return tokens[cursor] if cursor < len(tokens) else None

    def take() -> tuple[str, str]:
        nonlocal cursor
        cursor += 1
        return tokens[cursor - 1]

    def expression(depth: int) -> tuple:
        node = term(depth)
        while (item := peek()) and item[0] == "op" and item[1] in "+-":
            take()
            node = (item[1], node, term(depth))
        return node

    def term(depth: int) -> tuple:
        node = unary(depth)
        while (item := peek()) and item[0] == "op" and item[1] in "*/":
            take()
            node = (item[1], node, unary(depth))
        return node

    def unary(depth: int) -> tuple:
        if depth > _MAX_DEPTH:
            raise ThemeReferenceError("E_THEME_REF_SYNTAX", pointer, f"the expression nests deeper than {_MAX_DEPTH} levels")
        item = peek()
        if item and item[0] == "op" and item[1] == "-":
            take()
            return ("neg", unary(depth + 1))
        return primary(depth)

    def primary(depth: int) -> tuple:
        item = peek()
        if item is None:
            raise ThemeReferenceError("E_THEME_REF_SYNTAX", pointer, "the expression ends where an operand is expected")
        take()
        if item[0] == "number":
            return ("n", Decimal(item[1]))
        if item[0] == "ref":
            return ("r", item[1][1:-1].strip())
        if item[1] == "(":
            node = expression(depth + 1)
            closing = peek()
            if closing is None or closing[1] != ")":
                raise ThemeReferenceError("E_THEME_REF_SYNTAX", pointer, "a parenthesis is not closed")
            take()
            return node
        raise ThemeReferenceError("E_THEME_REF_SYNTAX", pointer, f"an operand is expected, found {item[1]!r}")

    tree = expression(0)
    if peek() is not None:
        raise ThemeReferenceError("E_THEME_REF_SYNTAX", pointer, f"unexpected {peek()[1]!r} after a complete expression")
    return tree


def _plain(value: Any) -> Decimal | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    result = Decimal(str(value))
    return result if result.is_finite() else None


def _written(value: Decimal) -> int | float:
    if value == value.to_integral_value():
        return int(value)
    return float(str(value.normalize()))


def resolve_references(theme: dict[str, Any]) -> dict[str, Any]:
    """The Theme with every number-token reference replaced by its value; the same object when none is used."""
    if not uses_references(theme):
        return theme
    values = theme["body"]["values"]
    result = deepcopy(theme)
    resolved: dict[str, Decimal] = {}
    written: dict[str, int | float] = {}

    def base(name: str) -> str:
        return f"/body/values/{_escape(name)}/value"

    def evaluate(name: str, stack: tuple[str, ...]) -> Decimal:
        if name in resolved:
            return resolved[name]
        entry = values[name]
        pointer = base(name)
        if entry.get("type") != "number":
            raise ThemeReferenceError("E_THEME_REF_TYPE", pointer, f"the token {name!r} has type {entry.get('type')!r}; only number tokens take part in a reference")
        source = _source(entry)
        if source is None:
            number = _plain(entry.get("value"))
            if number is None:
                raise ThemeReferenceError("E_THEME_REF_TYPE", pointer, f"the number token {name!r} has the non-number value {entry.get('value')!r}")
            resolved[name] = number
            written[name] = entry["value"]
            return number
        key, text = source
        pointer = f"{pointer}/{key}"
        if not isinstance(text, str) or not text.strip():
            raise ThemeReferenceError("E_THEME_REF_SYNTAX", pointer, f"`{key}` must be a non-empty string")
        tree = _parse(text if key == "expr" else "{" + text.strip("{} ") + "}", pointer)
        number = compute(tree, name, (*stack, name), pointer)
        resolved[name] = number
        written[name] = written[tree[1]] if tree[0] == "r" else _written(number)
        return number

    def lookup(target: str, owner: str, stack: tuple[str, ...], pointer: str) -> Decimal:
        if target not in values:
            raise ThemeReferenceError("E_THEME_REF_UNKNOWN", pointer, f"the token {owner!r} refers to {target!r}, which the Theme does not declare")
        if target in stack:
            loop = (*stack[stack.index(target):], target)
            raise ThemeReferenceError("E_THEME_REF_CYCLE", base(target), "Theme token references loop: " + " -> ".join(loop))
        return evaluate(target, stack)

    def compute(tree: tuple, owner: str, stack: tuple[str, ...], pointer: str) -> Decimal:
        kind = tree[0]
        if kind == "n":
            return tree[1]
        if kind == "r":
            return lookup(tree[1], owner, stack, pointer)
        if kind == "neg":
            return _CONTEXT.minus(compute(tree[1], owner, stack, pointer))
        left, right = compute(tree[1], owner, stack, pointer), compute(tree[2], owner, stack, pointer)
        try:
            return {"+": _CONTEXT.add, "-": _CONTEXT.subtract, "*": _CONTEXT.multiply, "/": _CONTEXT.divide}[kind](left, right)
        except (DivisionByZero, InvalidOperation) as error:
            raise ThemeReferenceError("E_THEME_REF_VALUE", pointer, f"the token {owner!r} divides by zero") from error

    for name in sorted(values):
        source = _source(values[name])
        if source is not None:
            evaluate(name, ())
            result["body"]["values"][name]["value"] = written[name]
    return result
