"""Explain why a tool's arguments broke its input schema: each violating node, the expected shape, where a member fits.

The MCP tool core turns these findings into ``rejected`` results (#1892 row 5), so an agent can fix the exact node
instead of reading a truncated input echoed back in a protocol error. Nothing here prints, reads files or echoes the
supplied value.
"""
from __future__ import annotations

import re
from typing import Any, Iterable, Mapping

from jsonschema.exceptions import ValidationError

from chrona.schema_diagnostics import explain_all_errors, violation_node, violation_sentence

_UNEXPECTED = re.compile(r"unexpected property '(.+?)'")




def _permitted_at(schema: Mapping[str, Any], name: str, limit: int = 3) -> list[str]:
    """Where in the input a member called ``name`` is permitted, as JSON pointers with ``*`` for a list item.

    Walks ``properties``, ``items``, the union and condition keywords and the schema's own ``#/$defs`` references, so an
    agent that put ``constraints`` one level too high or low is told the level that takes it.
    """
    found: list[str] = []

    def walk(node: Any, path: str, seen: frozenset[str]) -> None:
        if len(found) >= limit or not isinstance(node, Mapping):
            return
        reference = node.get("$ref")
        if isinstance(reference, str) and reference.startswith("#/$defs/") and reference not in seen:
            walk(schema.get("$defs", {}).get(reference[len("#/$defs/"):]), path, seen | {reference})
        properties = node.get("properties")
        if isinstance(properties, Mapping):
            if name in properties and path:
                found.append(path)
            for key, child in properties.items():
                walk(child, f"{path}/{str(key).replace('~', '~0').replace('/', '~1')}", seen)
        walk(node.get("items"), f"{path}/*", seen)
        for keyword in ("oneOf", "anyOf", "allOf"):
            for branch in node.get(keyword) or ():
                walk(branch, path, seen)
        for keyword in ("then", "else"):
            walk(node.get(keyword), path, seen)

    walk(schema, "", frozenset())
    return list(dict.fromkeys(found))


def _selected_leaves(errors: Iterable[ValidationError]) -> list[ValidationError]:
    """Replace each union failure by the violations of the one branch the instance was written for, when it can be told.

    A branch the instance's type already rules out (a path string beside inline objects) is not the branch the author
    meant, nor, among several, one whose ``const`` tag the instance does not carry. When exactly one remains, its own violations
    are the answer (``/command/payload/task``, not "expected one permitted form"); otherwise the union stays.
    """
    leaves: list[ValidationError] = []
    for error in errors:
        if error.validator in {"oneOf", "anyOf"} and error.context:
            branches: dict[Any, list[ValidationError]] = {}
            for child in error.context:
                branches.setdefault(child.schema_path[0] if child.schema_path else None, []).append(child)
            meant = [children for children in branches.values()
                     if not any(c.validator == "type" and not c.relative_path for c in children)]
            if len(meant) > 1:
                meant = [children for children in meant
                         if not any(c.validator == "const" and len(c.relative_path) == 1 for c in children)]
            if len(meant) == 1 and len(branches) == len(error.validator_value):
                leaves.extend(_selected_leaves(meant[0]))
                continue
        leaves.append(error)
    return leaves


def explain_input_errors(errors: Iterable[ValidationError], schema: Mapping[str, Any]) -> list[tuple[str, str]]:
    """``(pointer, message)`` for each violation: the node to fix, the expected shape and, for an unexpected property,
    where in ``schema`` that member is permitted (or that it is accepted nowhere)."""
    leaves = _selected_leaves(errors)
    if not leaves:
        return []
    found: list[tuple[str, str]] = []
    for violation in explain_all_errors(leaves, select_branches=True):
        message = violation_sentence(violation)
        unexpected = _UNEXPECTED.match(violation.message)
        if unexpected is not None:
            name = unexpected.group(1)
            where = _permitted_at(schema, name)
            message += (f"; '{name}' is permitted at {', '.join(where)}" if where
                        else f"; '{name}' is not accepted anywhere in this tool's input")
        found.append((violation_node(violation), message))
    return found
