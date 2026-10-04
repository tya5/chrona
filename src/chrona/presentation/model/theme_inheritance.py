"""Ingress-only resolution of the finite derived Theme source form."""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
from pathlib import Path, PurePosixPath
from typing import Any, Callable, Mapping

import yaml

from chrona.core.identity import content_identity
from chrona.core.ports import SnapshotReadError, SnapshotReader
from chrona.core.store_address import StoreAddressError, check_store_address, resolve_store_address
from chrona.resources import safe_load, schema_validator


class ThemeInheritanceError(ValueError):
    def __init__(self, code: str, detail: str = ""):
        super().__init__(code)
        self.code = code
        self.detail = detail


def is_derived_theme(value: object) -> bool:
    """Recognize derived Theme source forms before ordinary contract parsing."""
    return (isinstance(value, dict)
            and value.get("version") == "chrona/theme/v0.16")


def _safe_relative(address: object) -> PurePosixPath:
    if not isinstance(address, str):
        raise ThemeInheritanceError("E_THEME_INHERITANCE_PATH", f"a Theme path must be a string, got {address!r}")
    try:
        check_store_address(address)
    except StoreAddressError as error:
        raise ThemeInheritanceError("E_THEME_INHERITANCE_PATH", f"the Theme path {address!r} is not a safe relative address") from error
    return PurePosixPath(address)


def _validated_derived(value: dict[str, Any]) -> Mapping[str, Any]:
    version = value.get("version")
    schema_name = {"chrona/theme/v0.16": "theme-v0.16.schema.yaml"}.get(version)
    if schema_name is None:
        raise ThemeInheritanceError("E_THEME_INHERITANCE_SCHEMA",
                                    f"Theme version {version!r} is not a derived Theme version (chrona/theme/v0.16)")
    problems = tuple(schema_validator(schema_name).iter_errors(value))
    if problems:
        raise ThemeInheritanceError("E_THEME_INHERITANCE_SCHEMA",
                                    f"the derived Theme does not satisfy {schema_name}: {problems[0].message}")
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
        raise ThemeInheritanceError("E_THEME_INHERITANCE_SCHEMA", f"a Theme source is not valid YAML: {str(error).splitlines()[0]}") from error
    if not isinstance(value, dict):
        raise ThemeInheritanceError("E_THEME_INHERITANCE_SCHEMA", f"a Theme source must be a mapping, got {type(value).__name__}")
    return value


def _chain(keys: tuple[str, ...]) -> str:
    return " -> ".join(Path(key).name for key in keys)


def _source_identity(payload: bytes) -> str:
    return "sha256:" + sha256(payload).hexdigest()


BaseLoader = Callable[[str, Mapping[str, Any]], tuple[dict[str, Any], str, str]]


def _resolve(value: dict[str, Any], key: str, load_base: BaseLoader,
             stack: tuple[str, ...] = ()) -> dict[str, Any]:
    if key in stack:
        raise ThemeInheritanceError("E_THEME_INHERITANCE_CYCLE", f"Theme inheritance loops: {_chain((*stack, key))}")
    if not is_derived_theme(value):
        return value
    declaration = _validated_derived(value)
    base_value, source_identity, child_key = load_base(key, declaration)
    if child_key in (*stack, key):
        raise ThemeInheritanceError("E_THEME_INHERITANCE_CYCLE", f"Theme inheritance loops: {_chain((*stack, key, child_key))}")
    if source_identity != declaration["sourceContentIdentity"]:
        raise ThemeInheritanceError("E_THEME_INHERITANCE_SOURCE_IDENTITY",
                                    f"base Theme {Path(child_key).name} has source identity {source_identity}, "
                                    f"the derived Theme declares {declaration['sourceContentIdentity']}")
    base = _resolve(base_value, child_key, load_base, (*stack, key))
    expected_base_version = "chrona/theme/v0.15"
    if (base.get("kind") != "theme" or base.get("version") != expected_base_version
            or base.get("id") != declaration["id"]):
        raise ThemeInheritanceError("E_THEME_INHERITANCE_BASE_KIND",
                                    f"base {Path(child_key).name} is {base.get('kind')} {base.get('version')} {base.get('id')!r}; "
                                    f"expected a theme {expected_base_version} with id {declaration['id']!r}")
    if content_identity(base) != declaration["contentIdentity"]:
        raise ThemeInheritanceError("E_THEME_INHERITANCE_BASE_IDENTITY",
                                    f"base Theme {declaration['id']!r} has content identity {content_identity(base)}, "
                                    f"the derived Theme declares {declaration['contentIdentity']}")
    effective = deepcopy(base)
    effective["id"] = value["id"]
    body = effective.get("body")
    if not isinstance(body, dict):
        raise ThemeInheritanceError("E_THEME_INHERITANCE_EFFECTIVE_SCHEMA", "the base Theme has no body mapping")
    for name in ("values", "roles"):
        replacement, target = value["body"].get(name, {}), body.get(name)
        if not isinstance(target, dict):
            raise ThemeInheritanceError("E_THEME_INHERITANCE_EFFECTIVE_SCHEMA", f"body.{name} of the base Theme is not a mapping")
        unknown = [entry for entry in replacement if entry not in target]
        if unknown:
            raise ThemeInheritanceError("E_THEME_INHERITANCE_OVERRIDE_UNKNOWN",
                                        f"body.{name} overrides entries the base Theme does not declare: {unknown}")
        target.update(deepcopy(replacement))
    effective_schema = "theme-v0.15.schema.yaml"
    problems = tuple(schema_validator(effective_schema).iter_errors(effective))
    if problems:
        raise ThemeInheritanceError("E_THEME_INHERITANCE_EFFECTIVE_SCHEMA",
                                    f"the resolved Theme does not satisfy {effective_schema}: {problems[0].message}")
    return effective


def resolve_draft_theme(path: Path, *, payload: bytes | None = None) -> dict[str, Any]:
    """Resolve local source bytes into an ordinary complete Theme value."""
    try:
        source = path.read_bytes() if payload is None else payload
    except OSError as error:
        raise ThemeInheritanceError("E_THEME_INHERITANCE_BASE_MISSING", f"cannot read the Theme source {path.name}: {error.strerror or error}") from error

    def load_base(parent_key: str, declaration: Mapping[str, Any]) -> tuple[dict[str, Any], str, str]:
        parent = Path(parent_key)
        try:
            child = resolve_store_address(parent.parent, declaration["path"])
        except StoreAddressError as error:
            raise ThemeInheritanceError("E_THEME_INHERITANCE_PATH",
                                        f"the base Theme path {declaration['path']!r} is not a safe relative address") from error
        try:
            raw = child.read_bytes()
        except OSError as error:
            raise ThemeInheritanceError("E_THEME_INHERITANCE_BASE_MISSING",
                                        f"cannot read the base Theme {child.name}: {error.strerror or error}") from error
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
            raise ThemeInheritanceError(code, f"the base Theme {child['address']!r} could not be read from the snapshot: "
                                              f"{error.detail or error.diagnostic_id}") from error
        return _decoded(raw), _source_identity(raw), child["address"]

    return _resolve(value, str(reference["address"]), load_base)
