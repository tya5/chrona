"""Ingress-only resolution of a derived Layout Profile (`extends` plus `overrides`) into a standalone profile (#1342).

The base is an ordinary pinned reference, so it may live in any Store the reader reads (the example's own, a shared design
Store or the packaged store). Reading verifies the base's `contentIdentity`; the flattened profile carries the content
identity of the effective value, so editing a base moves every derived profile's identity and no Context.
"""
from __future__ import annotations

from typing import Any, Mapping

from chrona.core.ports import SnapshotReader, SnapshotReadError
from chrona.presentation.layout.model import LayoutError
from chrona.presentation.layout.profile import LayoutBase, flatten_layout_profile
from chrona.resources import safe_load


class LayoutInheritanceError(ValueError):
    def __init__(self, code: str, detail: str = ""):
        super().__init__(code)
        self.code = code
        self.detail = detail


def is_derived_layout(value: object) -> bool:
    return isinstance(value, dict) and "extends" in value and "root" not in value


def resolve_snapshot_layout(value: dict[str, Any], reader: SnapshotReader) -> dict[str, Any]:
    """Flatten ``value`` by reading its base chain through ``reader``; a standalone profile is returned unchanged."""
    return _flatten(value, reader, ())


def _flatten(value: dict[str, Any], reader: SnapshotReader, stack: tuple[tuple[Any, ...], ...]) -> dict[str, Any]:
    if not is_derived_layout(value):
        return value
    reference = value["extends"]
    store = reference.get("store", {}) if isinstance(reference, Mapping) else {}
    key = (store.get("provider"), store.get("identity"), reference.get("address"))
    if key in stack:
        raise LayoutInheritanceError("E_LAYOUT_BASE_CYCLE", f"Layout inheritance repeats {key[2]!r}")
    try:
        payload = reader.read(reference)
    except SnapshotReadError as error:
        raise LayoutInheritanceError(error.diagnostic_id, f"base Layout {reference.get('id')!r}: {error.detail}") from error
    base = safe_load(payload)
    if not isinstance(base, dict) or base.get("id") != reference.get("id"):
        raise LayoutInheritanceError("E_CLOSURE_ID", f"base Layout reference {reference.get('id')!r} names a profile whose own id is "
                                     f"{base.get('id') if isinstance(base, dict) else type(base).__name__!r}")
    resolved = _flatten(base, reader, (*stack, key))
    bases = {str(reference["id"]): LayoutBase(resolved, reference["revision"]["token"], reference["contentIdentity"])}
    try:
        return flatten_layout_profile(value, bases)
    except LayoutError as error:
        raise LayoutInheritanceError(error.diagnostic_id, f"{error.path} {error.detail}".strip()) from error
