"""Where a diagnostic's node is in a YAML source: line and column of the offending key or value (#1303).

A Project is often written in flow style, so a whole object is one line and an author cannot map a JSON Pointer by
hand. The range is the node's own start, found by walking the pointer through the composed YAML; a pointer that names a
member the file lacks (a missing required property) resolves to the deepest node that exists, and an unexpected member
named in the message resolves to its own key.
"""
from __future__ import annotations

from collections.abc import Iterable
from dataclasses import replace
import re

import yaml
from yaml.nodes import MappingNode, Node, ScalarNode, SequenceNode

from chrona.core.diagnostics import Diagnostic

_UNEXPECTED = re.compile(r"unexpected property '([^']+)'")


def _tokens(pointer: str) -> list[str]:
    return [item.replace("~1", "/").replace("~0", "~") for item in pointer.split("/")[1:]] if pointer not in {"", "/"} else []


def _mark_range(node: Node) -> dict[str, int]:
    line, column = node.start_mark.line + 1, node.start_mark.column + 1
    width = len(node.value) if isinstance(node, ScalarNode) and "\n" not in node.value else 1
    return {"line": line, "column": column, "endLine": line, "endColumn": column + max(width, 1)}


def locate(root: Node | None, pointer: str, member: str | None = None) -> dict[str, int] | None:
    """The source range of `pointer` in a composed YAML document (a key's own range for a mapping member)."""
    if root is None:
        return None
    node, found = root, root
    for token in _tokens(pointer):
        key_node: Node | None = None
        if isinstance(node, MappingNode):
            for key, value in node.value:
                if isinstance(key, ScalarNode) and key.value == token:
                    key_node, node = key, value
                    break
            else:
                break
        elif isinstance(node, SequenceNode) and token.isdigit() and int(token) < len(node.value):
            node = node.value[int(token)]
        else:
            break
        found = key_node if key_node is not None else node
    if member is not None and isinstance(node, MappingNode):
        for key, _ in node.value:
            if isinstance(key, ScalarNode) and key.value == member:
                return _mark_range(key)
    return _mark_range(found)


def attach_ranges(diagnostics: Iterable[Diagnostic], text: str) -> tuple[Diagnostic, ...]:
    """The diagnostics with a `source_range` from a YAML text; unchanged when the text does not compose."""
    items = tuple(diagnostics)
    try:
        root = yaml.compose(text, Loader=yaml.SafeLoader)
    except yaml.YAMLError:
        return items
    found = []
    for item in items:
        member = _UNEXPECTED.search(item.message)
        located = locate(root, item.path or "/", member.group(1) if member else None)
        found.append(replace(item, source_range=located) if located is not None else item)
    return tuple(found)
