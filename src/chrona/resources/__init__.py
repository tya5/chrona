"""Locations for source-tree and wheel-installed runtime resources."""
from __future__ import annotations

from copy import deepcopy
from functools import cache
from importlib.resources import files
from importlib.resources.abc import Traversable
import json
from pathlib import PurePosixPath
from typing import Any, Mapping

from jsonschema import Draft202012Validator
from referencing import Registry, Resource
import yaml


_SAFE_LOADER = getattr(yaml, "CSafeLoader", yaml.SafeLoader)


def safe_load(source: Any) -> Any:
    """Safely decode YAML, using JSON's fast path for JSON-subset resources."""
    if isinstance(source, bytes):
        stripped = source.lstrip()
        if stripped.startswith(b"{"):
            try:
                return json.loads(stripped)
            except json.JSONDecodeError:
                pass
        return yaml.load(source, Loader=_SAFE_LOADER)
    elif isinstance(source, str):
        stripped = source.lstrip()
        if stripped.startswith("{"):
            try:
                return json.loads(stripped)
            except json.JSONDecodeError:
                pass
        return yaml.load(source, Loader=_SAFE_LOADER)
    else:
        return yaml.load(source, Loader=_SAFE_LOADER)


def schema_resource(name: str) -> Traversable:
    """Return a schema from the wheel, or from the sole source-tree authority."""
    packaged = files(__package__).joinpath("schemas", name)
    if packaged.is_file():
        return packaged
    return files("schemas").joinpath(name)


def skill_resource() -> Traversable:
    """Return the chrona agent skill from the wheel, or from the sole source-tree authority."""
    packaged = files(__package__).joinpath("skills", "chrona")
    if packaged.is_dir() and packaged.joinpath("SKILL.md").is_file():
        return packaged
    try:
        source = files("skills").joinpath("chrona")
    except ModuleNotFoundError as error:
        raise ValueError("E_SKILL_RESOURCE: the chrona skill is not packaged (no chrona/resources/skills/chrona in the wheel, no skills package in the source tree)") from error
    if source.is_dir() and source.joinpath("SKILL.md").is_file():
        return source
    raise ValueError("E_SKILL_RESOURCE: skills/chrona has no SKILL.md")


@cache
def example_registry() -> Mapping[str, Mapping[str, str]]:
    """Return the initialisable examples by id, validated against the registry schema."""
    value = safe_load(files(__package__).joinpath("example-registry.yaml").read_bytes())
    if not isinstance(value, Mapping) or tuple(schema_validator("example-registry-v0.1.schema.yaml").iter_errors(value)):
        raise ValueError("E_EXAMPLE_REGISTRY: example-registry.yaml is not a mapping that satisfies example-registry-v0.1.schema.yaml")
    return {entry["id"]: entry for entry in value["examples"]}


def example_ids() -> tuple[str, ...]:
    """Return the ids `chrona init --example` accepts."""
    return tuple(example_registry())


def template_resource(name: str) -> Traversable:
    """Return one registered init example from the wheel or development authority."""
    entry = example_registry().get(name)
    if entry is None:
        raise ValueError(f"E_INIT_EXAMPLE: {name!r} is not registered; available: {', '.join(example_ids())}")
    parts = PurePosixPath(entry["path"]).parts
    packaged = files(__package__).joinpath(*parts)
    if _is_example(packaged):
        return packaged
    source = files(parts[0]).joinpath(*parts[1:])
    if _is_example(source):
        return source
    raise ValueError(f"E_INIT_EXAMPLE: example {name!r} is registered at {entry['path']} but that directory has neither a manifest.yaml nor stage directories with a project.yaml in the wheel or the source tree")


def _is_example(node: Traversable) -> bool:
    """A corpus (a `manifest.yaml`) or a set of numbered stages (each directory holds a `project.yaml`)."""
    if not node.is_dir():
        return False
    if node.joinpath("manifest.yaml").is_file():
        return True
    return any(child.is_dir() and child.joinpath("project.yaml").is_file() for child in node.iterdir())


def minimal_template_resource() -> Traversable:
    """Return the wheel-owned editable starter template, not a corpus example."""
    resource = files(__package__).joinpath("templates", "minimal")
    required = ("project.yaml", "actual.yaml", "README.md")
    if not resource.is_dir() or any(not resource.joinpath(name).is_file() for name in required):
        missing = [name for name in required if not resource.joinpath(name).is_file()] if resource.is_dir() else ["templates/minimal"]
        raise ValueError(f"E_INIT_TEMPLATE: the packaged starter template is missing {', '.join(missing)}")
    return resource


def default_preset_resource() -> Traversable:
    """Return the wheel-owned draft default preset without repository lookup."""
    resource = files(__package__).joinpath("presets", "default.yaml")
    if not resource.is_file():
        raise ValueError("E_DRAFT_DEFAULT_PRESET: the packaged default preset presets/default.yaml is missing")
    return resource


def builtin_preset_library_resource() -> Traversable:
    """Return the finite wheel-owned builtin preset catalogue."""
    resource = files(__package__).joinpath("presets", "library.yaml")
    if not resource.is_file():
        raise ValueError("E_BUILTIN_PRESET_LIBRARY: the packaged preset catalogue presets/library.yaml is missing")
    return resource


def axis_name_tables_resource() -> Traversable:
    """Return the finite, wheel-owned axis vocabulary catalog."""
    resource = files(__package__).joinpath("axis-name-tables-v0.1.yaml")
    if not resource.is_file():
        raise ValueError("E_AXIS_NAME_TABLE_RESOURCE: the packaged axis-name-tables-v0.1.yaml is missing")
    return resource


def builtin_preset_source_root(address: str) -> Traversable:
    """Resolve one safe builtin-library source root in wheel or source authority."""
    path = PurePosixPath(address)
    if (not address or path.is_absolute() or address != path.as_posix()
            or any(part in {"", ".", ".."} for part in path.parts)):
        raise ValueError(f"E_BUILTIN_PRESET_LIBRARY: source root {address!r} is not a safe relative address")
    packaged = files(__package__).joinpath(*path.parts)
    if path.parts == ("icons",) and packaged.is_dir():
        return packaged
    if packaged.is_dir() and (
        packaged.joinpath("project.yaml").is_file()
        or path.parts[:2] == ("presets", "bundles")
    ):
        return packaged
    raise ValueError(f"E_BUILTIN_PRESET_RESOURCE: source root {address!r} is not packaged")


def default_preset_root() -> Traversable:
    """Return the packaged presets root that every path of the bundled default is relative to."""
    root = files(__package__).joinpath("presets")
    if not root.joinpath("default.yaml").is_file():
        raise ValueError("E_DRAFT_DEFAULT_PRESET: the packaged presets root has no default.yaml")
    return root


@cache
def schema_document(name: str) -> Mapping[str, Any]:
    """Decode one immutable schema resource once per process."""
    value = safe_load(schema_resource(name).read_bytes())
    if not isinstance(value, Mapping):
        raise ValueError(f"E_SCHEMA_RESOURCE: {name}")
    return value


SCHEMA_PARTS: tuple[str, ...] = (
    "common-v0.1.schema.yaml",
    "graphics-v0.1.schema.yaml",
    "presentation-resource-v0.1.schema.yaml",
    "revision-store-resource-ref-v0.1.schema.yaml",
    "revision-store-resource-ref-v0.2.schema.yaml",
    "vocabulary-v0.1.schema.yaml",
)
"""Schema files that other schemas may reference by their `urn:chrona:` `$id`.

A part is available to `$ref` only by being listed here, so a stray or archived
schema file can never become a reference target.
"""


@cache
def schema_registry() -> Registry:
    """Return the registry of every schema part, loaded eagerly.

    A missing or malformed part raises here, when the registry is first built,
    rather than lazily when some document reaches a `$ref` to it.
    """
    registry: Registry = Registry()
    for name in SCHEMA_PARTS:
        part = schema_document(name)
        registry = registry.with_resource(part["$id"], Resource.from_contents(part))
    # Crawl once: a registry that is not crawled re-crawls on every lookup.
    return registry.crawl()


def validator_for_schema(schema: Mapping[str, Any]) -> Draft202012Validator:
    """Build a validator over an arbitrary schema document with the part registry.

    Use this for a caller-supplied schema (an override path, a schema read from
    a foreign root); `schema_validator` is the cached form for a packaged name.
    """
    return Draft202012Validator(schema, registry=schema_registry())


@cache
def schema_validator(name: str) -> Draft202012Validator:
    """Return the shared validator of one packaged schema, cached by name.

    This is the only place in `src/`, `tools/` and `conformance/` that
    constructs a validator; a guard test enforces that.
    """
    return validator_for_schema(schema_document(name))


def _part_ids() -> dict[str, str]:
    return {schema_document(name)["$id"]: name for name in SCHEMA_PARTS}


def _external_ref_targets(node: Any, part_ids: Mapping[str, str]) -> set[str]:
    found: set[str] = set()
    if isinstance(node, Mapping):
        for key, value in node.items():
            if key == "$ref" and isinstance(value, str) and value.partition("#")[0] in part_ids:
                found.add(value.partition("#")[0])
            else:
                found |= _external_ref_targets(value, part_ids)
    elif isinstance(node, list):
        for item in node:
            found |= _external_ref_targets(item, part_ids)
    return found


def bundled_schema(name: str) -> dict[str, Any]:
    """Return a schema with each referenced part embedded under `$defs` by its `$id`.

    This is the JSON Schema 2020-12 compound-document form: a bare validator with
    no registry validates it.
    """
    part_ids = _part_ids()
    bundled = deepcopy(dict(schema_document(name)))
    pending = sorted(_external_ref_targets(bundled, part_ids))
    embedded: dict[str, Any] = {}
    while pending:
        part_id = pending.pop()
        if part_id in embedded:
            continue
        embedded[part_id] = deepcopy(dict(schema_document(part_ids[part_id])))
        pending.extend(sorted(_external_ref_targets(embedded[part_id], part_ids) - set(embedded)))
    if embedded:
        defs = dict(bundled.get("$defs", {}))
        defs.update(embedded)
        bundled["$defs"] = defs
    return bundled


def resolve_schema_reference(document: Mapping[str, Any], reference: str) -> tuple[Mapping[str, Any], Mapping[str, Any]] | None:
    """Follow one `$ref` of `document` and return the document that owns the target and the target node.

    A local `#/...` reference resolves inside `document`; an external reference resolves inside the registered
    schema part that carries that `$id`. The owning document is returned because references inside the target
    are local to it. `None` means the reference is not followable (an unknown target or a missing pointer).
    For analysis readers that walk a schema without a validator.
    """
    target, _, fragment = reference.partition("#")
    if not target:
        if not fragment.startswith("/"):
            return None
        owner: Mapping[str, Any] | None = document
    else:
        name = _part_ids().get(target)
        owner = schema_document(name) if name is not None else None
    if owner is None:
        return None
    node: Any = owner
    for token in [item for item in fragment.split("/") if item]:
        node = node.get(token.replace("~1", "/").replace("~0", "~")) if isinstance(node, Mapping) else None
    return (owner, node) if isinstance(node, Mapping) else None


def dereferenced_schema(name: str) -> dict[str, Any]:
    """Return a schema with every external part `$ref` replaced by its target subtree.

    Local references inside a replaced subtree are resolved as well. The schema's
    own local references are left alone. For analysis only, never for validation.
    """
    part_ids = _part_ids()

    def resolve_pointer(document: Any, fragment: str) -> Any:
        node = document
        for token in [item for item in fragment.split("/") if item]:
            node = node[token.replace("~1", "/").replace("~0", "~")]
        return node

    def inline(node: Any, part: Mapping[str, Any] | None, stack: tuple[str, ...]) -> Any:
        if isinstance(node, list):
            return [inline(item, part, stack) for item in node]
        if not isinstance(node, Mapping):
            return node
        ref = node.get("$ref")
        if isinstance(ref, str):
            target, _, fragment = ref.partition("#")
            document: Mapping[str, Any] | None
            if target in part_ids:
                document = schema_document(part_ids[target])
            elif part is not None and not target:
                document = part
            else:
                document = None
            if document is not None:
                key = f"{document['$id']}#{fragment}"
                if key in stack:
                    raise ValueError(f"E_SCHEMA_REF_CYCLE: {name}: {ref}")
                resolved = inline(resolve_pointer(document, fragment), document, (*stack, key))
                if not fragment and isinstance(resolved, Mapping):
                    resolved = {k: v for k, v in resolved.items() if k not in {"$id", "$schema"}}
                siblings = {k: inline(v, part, stack) for k, v in node.items() if k != "$ref"}
                return {**resolved, **siblings} if siblings and isinstance(resolved, Mapping) else resolved
        return {key: inline(value, part, stack) for key, value in node.items()}

    return inline(schema_document(name), None, ())
