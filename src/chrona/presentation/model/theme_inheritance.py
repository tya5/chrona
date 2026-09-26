"""Ingress-only resolution of the finite derived Theme source form."""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
from pathlib import Path, PurePosixPath
from typing import Any, Callable, Mapping

import jsonschema
import yaml

from chrona.core.identity import content_identity
from chrona.core.ports import SnapshotReadError, SnapshotReader
from chrona.resources import safe_load, schema_document


class ThemeInheritanceError(ValueError):
    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def is_derived_theme(value: object) -> bool:
    """Recognize the source syntax before ordinary Theme contract parsing."""
    return isinstance(value, dict) and value.get("version") == "chrona/theme/v0.12"


def _safe_relative(address: object) -> PurePosixPath:
    if not isinstance(address, str):
        raise ThemeInheritanceError("E_THEME_INHERITANCE_PATH")
    path = PurePosixPath(address)
    if (not address or path.is_absolute() or address != path.as_posix()
            or any(part in {"", ".", ".."} for part in path.parts)):
        raise ThemeInheritanceError("E_THEME_INHERITANCE_PATH")
    return path


def _validated_derived(value: dict[str, Any]) -> Mapping[str, Any]:
    schema = schema_document("theme-v0.12.schema.yaml")
    if tuple(jsonschema.Draft202012Validator(schema).iter_errors(value)):
        raise ThemeInheritanceError("E_THEME_INHERITANCE_SCHEMA")
    return value["body"]["extends"]


def theme_base_reference(parent: Mapping[str, Any], derived: dict[str, Any]) -> dict[str, Any]:
    """Build the sole allowed same-store, same-revision base source edge."""
    return _child_reference(parent, _validated_derived(derived))


def _child_reference(parent: Mapping[str, Any], declaration: Mapping[str, Any]) -> dict[str, Any]:
    parent_address = _safe_relative(parent.get("address"))
    child_address = parent_address.parent.joinpath(_safe_relative(declaration["path"]))
    return {
        "id": declaration["id"],
        "kind": "theme",
        "store": parent["store"],
        "address": child_address.as_posix(),
        "revision": parent["revision"],
        "contentIdentity": declaration["sourceContentIdentity"],
    }


def _decoded(payload: bytes) -> dict[str, Any]:
    try:
        value = safe_load(payload)
    except yaml.YAMLError as error:
        raise ThemeInheritanceError("E_THEME_INHERITANCE_SCHEMA") from error
    if not isinstance(value, dict):
        raise ThemeInheritanceError("E_THEME_INHERITANCE_SCHEMA")
    return value


def _source_identity(payload: bytes) -> str:
    return "sha256:" + sha256(payload).hexdigest()


BaseLoader = Callable[[str, Mapping[str, Any]], tuple[dict[str, Any], str, str]]


def _resolve(value: dict[str, Any], key: str, load_base: BaseLoader,
             stack: tuple[str, ...] = ()) -> dict[str, Any]:
    if key in stack:
        raise ThemeInheritanceError("E_THEME_INHERITANCE_CYCLE")
    if not is_derived_theme(value):
        return value
    declaration = _validated_derived(value)
    base_value, source_identity, child_key = load_base(key, declaration)
    if child_key in (*stack, key):
        raise ThemeInheritanceError("E_THEME_INHERITANCE_CYCLE")
    if source_identity != declaration["sourceContentIdentity"]:
        raise ThemeInheritanceError("E_THEME_INHERITANCE_SOURCE_IDENTITY")
    base = _resolve(base_value, child_key, load_base, (*stack, key))
    if (base.get("kind") != "theme" or base.get("version") != "chrona/theme/v0.11"
            or base.get("id") != declaration["id"]):
        raise ThemeInheritanceError("E_THEME_INHERITANCE_BASE_KIND")
    if content_identity(base) != declaration["contentIdentity"]:
        raise ThemeInheritanceError("E_THEME_INHERITANCE_BASE_IDENTITY")
    effective = deepcopy(base)
    effective["id"] = value["id"]
    body = effective.get("body")
    if not isinstance(body, dict):
        raise ThemeInheritanceError("E_THEME_INHERITANCE_EFFECTIVE_SCHEMA")
    for name in ("values", "roles"):
        replacement, target = value["body"].get(name, {}), body.get(name)
        if not isinstance(target, dict):
            raise ThemeInheritanceError("E_THEME_INHERITANCE_EFFECTIVE_SCHEMA")
        if any(entry not in target for entry in replacement):
            raise ThemeInheritanceError("E_THEME_INHERITANCE_OVERRIDE_UNKNOWN")
        target.update(deepcopy(replacement))
    schema = schema_document("theme-v0.11.schema.yaml")
    if tuple(jsonschema.Draft202012Validator(schema).iter_errors(effective)):
        raise ThemeInheritanceError("E_THEME_INHERITANCE_EFFECTIVE_SCHEMA")
    return effective


def resolve_draft_theme(path: Path, *, payload: bytes | None = None) -> dict[str, Any]:
    """Resolve local source bytes into an ordinary complete Theme value."""
    try:
        source = path.read_bytes() if payload is None else payload
    except OSError as error:
        raise ThemeInheritanceError("E_THEME_INHERITANCE_BASE_MISSING") from error

    def load_base(parent_key: str, declaration: Mapping[str, Any]) -> tuple[dict[str, Any], str, str]:
        parent = Path(parent_key)
        child = parent.parent.joinpath(_safe_relative(declaration["path"])).resolve()
        if parent.parent != child and parent.parent not in child.parents:
            raise ThemeInheritanceError("E_THEME_INHERITANCE_PATH")
        try:
            raw = child.read_bytes()
        except OSError as error:
            raise ThemeInheritanceError("E_THEME_INHERITANCE_BASE_MISSING") from error
        return _decoded(raw), _source_identity(raw), str(child)

    return _resolve(_decoded(source), str(path.resolve()), load_base)


def resolve_snapshot_theme(value: dict[str, Any], reference: Mapping[str, Any],
                           reader: SnapshotReader) -> dict[str, Any]:
    """Resolve declared Theme edges only through the immutable snapshot reader."""
    def load_base(parent_address: str, declaration: Mapping[str, Any]) -> tuple[dict[str, Any], str, str]:
        parent = {**reference, "address": parent_address}
        child = _child_reference(parent, declaration)
        try:
            raw = reader.read(child)
        except SnapshotReadError as error:
            code = ("E_THEME_INHERITANCE_SOURCE_IDENTITY" if error.diagnostic_id == "E_CONTENT_IDENTITY"
                    else "E_THEME_INHERITANCE_BASE_MISSING")
            raise ThemeInheritanceError(code) from error
        return _decoded(raw), _source_identity(raw), child["address"]

    return _resolve(value, str(reference["address"]), load_base)
