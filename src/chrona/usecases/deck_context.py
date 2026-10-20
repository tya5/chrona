"""Select and compose an example manifest's explicit Render Context source.

The result is still an ordinary immutable Render Context input.  This module
does not resolve resource references, stage files, or render a review.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping

import yaml

from chrona.core.source_ranges import locate
from chrona.core.store_address import StoreAddressError, check_store_segment, resolve_store_address
from chrona.resources import safe_load, schema_validator
from chrona.schema_diagnostics import explain_errors
from chrona.usecases.failure_report import StableFailure


@dataclass(frozen=True)
class SourceOrigin:
    """The manifest/context source node that supplied a completed pointer."""

    path: Path
    source_ref: str
    source_range: Mapping[str, int] | None = None


@dataclass(frozen=True)
class DeckManifest:
    """One strictly decoded materializer manifest, reusable across its slides."""

    path: Path
    payload: bytes
    document: Mapping[str, Any]
    node: yaml.Node | None


@dataclass(frozen=True)
class SelectedDeckContext:
    """The single selected, completed Context source consumed by materializers."""

    document: Mapping[str, Any]
    payload: bytes
    address: str
    source_path: Path | None
    manifest_path: Path
    slide_id: str
    source_mode: str
    origins: Mapping[str, SourceOrigin]

    @property
    def body(self) -> Mapping[str, Any]:
        return self.document.get("body", {})


def _pointer(tokens: tuple[str, ...] | list[str]) -> str:
    def escape(item: object) -> str:
        return str(item).replace("~", "~0").replace("/", "~1")
    return "/" + "/".join(escape(item) for item in tokens) if tokens else "/"


def _fail(code: str, message: str, source_ref: str = "/") -> StableFailure:
    return StableFailure(code, message, "materializer", source_ref)


def _inspect_yaml(node: yaml.Node | None, path: Path) -> None:
    """Reject YAML graph/mapping features that safe_load would erase or recurse through."""
    active: set[int] = set()

    def walk(current: yaml.Node, tokens: tuple[str, ...]) -> None:
        marker = id(current)
        if marker in active:
            raise _fail("E_MATERIALIZER_YAML_CYCLE",
                        f"{path.name}: cyclic YAML aliases are not permitted", _pointer(tokens))
        if not isinstance(current, (yaml.MappingNode, yaml.SequenceNode)):
            return
        active.add(marker)
        try:
            if isinstance(current, yaml.MappingNode):
                seen: set[str] = set()
                for key, value in current.value:
                    if isinstance(key, yaml.ScalarNode) and key.tag == "tag:yaml.org,2002:merge":
                        raise _fail("E_MATERIALIZER_YAML_MERGE",
                                    f"{path.name}: YAML mapping merges are not permitted", _pointer(tokens))
                    if not isinstance(key, yaml.ScalarNode) or key.tag != "tag:yaml.org,2002:str":
                        raise _fail("E_MATERIALIZER_YAML_KEY",
                                    f"{path.name}: mapping keys must be strings", _pointer(tokens))
                    name = key.value
                    child = (*tokens, name)
                    if name in seen:
                        raise _fail("E_MATERIALIZER_YAML_DUPLICATE",
                                    f"{path.name}: duplicate mapping key {name!r}", _pointer(child))
                    seen.add(name)
                    walk(value, child)
            else:
                for index, value in enumerate(current.value):
                    walk(value, (*tokens, str(index)))
        finally:
            active.remove(marker)

    if node is not None:
        walk(node, ())


def _parse_source(path: Path, *, strict_manifest: bool = True) -> tuple[bytes, Any, yaml.Node | None]:
    try:
        payload = path.read_bytes()
        text = payload.decode("utf-8")
        node = yaml.compose(text, Loader=yaml.SafeLoader)
        if strict_manifest:
            _inspect_yaml(node, path)
        document = safe_load(payload)
    except StableFailure:
        raise
    except (OSError, UnicodeError) as error:
        raise _fail("E_INPUT_IO", f"cannot read YAML source {path.name}: {error}") from error
    except yaml.YAMLError as error:
        raise _fail("E_INPUT_YAML", f"invalid YAML in {path.name}: {error}") from error
    return payload, document, node


def _schema_error(document: Mapping[str, Any], source_path: Path, node: yaml.Node | None,
                  *, slide_id: str, fallback_ref: str) -> None:
    validator = schema_validator("example-materializer-v0.1.schema.yaml")
    errors = tuple(validator.iter_errors(document))
    if not errors:
        return
    leaves = tuple(_deep_errors(errors))
    deepest = max(len(error.absolute_path) for error in leaves)
    violation = explain_errors(error for error in leaves if len(error.absolute_path) == deepest)
    pointer = violation.pointer
    error = _matching_error(errors, pointer, violation.rule)
    if violation.rule == "additionalProperties" and error is not None and isinstance(error.instance, Mapping):
        declared = set(error.schema.get("properties", {})) if isinstance(error.schema, Mapping) else set()
        unknown = sorted((str(key) for key in error.instance if key not in declared))
        if unknown:
            pointer = pointer.rstrip("/") + "/" + unknown[0].replace("~", "~0").replace("/", "~1")
    source_ref = pointer if pointer != "/" else fallback_ref
    message = f"while selecting slide {slide_id}: {violation.message}"
    source_range = locate(node, source_ref) if node is not None else None
    if source_range:
        message += f" (line {source_range['line']}, column {source_range['column']})"
    raise _fail("E_MATERIALIZER_MANIFEST_SCHEMA", message, source_ref)


def _matching_error(errors: tuple[Any, ...], pointer: str, rule: str) -> Any | None:
    """Find the validator leaf selected by the shared stable schema reporter."""
    def walk(error: Any):
        if _pointer(tuple(str(token) for token in error.absolute_path)) == pointer and error.validator == rule:
            yield error
        for child in error.context:
            yield from walk(child)
    return next((error for candidate in errors for error in walk(candidate)), None)


def _deep_errors(errors: tuple[Any, ...]):
    """Expose nested applicator failures so source pointers name the bad leaf value."""
    for error in errors:
        if error.context:
            yield from _deep_errors(tuple(error.context))
        else:
            yield error


def _origins(node: yaml.Node | None, path: Path, prefix: str = "") -> dict[str, SourceOrigin]:
    result: dict[str, SourceOrigin] = {}
    active: set[int] = set()

    def visit(current: yaml.Node, tokens: tuple[str, ...]) -> None:
        marker = id(current)
        if marker in active:
            return
        active.add(marker)
        pointer = _pointer(tokens)
        result[pointer] = SourceOrigin(path, pointer, locate(node, pointer))
        try:
            if isinstance(current, yaml.MappingNode):
                for key, value in current.value:
                    if isinstance(key, yaml.ScalarNode) and key.tag == "tag:yaml.org,2002:str":
                        visit(value, (*tokens, key.value))
            elif isinstance(current, yaml.SequenceNode):
                for index, value in enumerate(current.value):
                    visit(value, (*tokens, str(index)))
        finally:
            active.remove(marker)

    if node is not None:
        visit(node, tuple(token for token in prefix.split("/") if token))
    return result


def load_deck_manifest(path: Path) -> DeckManifest:
    """Read and strictly parse one manifest; callers may select many slides from it."""
    resolved = path.resolve()
    payload, document, node = _parse_source(resolved)
    if not isinstance(document, Mapping):
        raise _fail("E_MATERIALIZER_MANIFEST", f"{resolved.name} must contain a manifest mapping")
    return DeckManifest(resolved, payload, MappingProxyType(dict(document)), node)


def select_deck_context(manifest_path: Path, manifest: DeckManifest,
                        slide_id: str) -> SelectedDeckContext:
    """Select one authored Context or compose its defaults with slide overrides."""
    if manifest.path != manifest_path.resolve():
        raise _fail("E_MATERIALIZER_MANIFEST", "manifest path does not match its loaded document")
    raw = dict(manifest.document)
    slides = raw.get("slides")
    if not isinstance(slides, list):
        raise _fail("E_MATERIALIZER_MANIFEST", "manifest slides must be a list", "/slides")
    seen_ids: dict[str, int] = {}
    for index, item in enumerate(slides):
        if isinstance(item, Mapping) and isinstance(item.get("id"), str):
            current_id = item["id"]
            if current_id in seen_ids:
                raise _fail("E_MATERIALIZER_SLIDE_ID_DUPLICATE",
                            f"slide id {current_id!r} is declared more than once",
                            f"/slides/{index}/id")
            seen_ids[current_id] = index
    slide_index = next((index for index, item in enumerate(slides)
                        if isinstance(item, Mapping) and item.get("id") == slide_id), None)
    if slide_index is None:
        raise _fail("E_MATERIALIZER_SLIDE", f"slide {slide_id!r} is not declared", "/slides")
    slide = dict(slides[slide_index])

    # The manifest is one authored declaration: malformed unselected slides
    # cannot be hidden by selecting a different slide.
    _schema_error(raw, manifest.path, manifest.node, slide_id=slide_id,
                  fallback_ref=f"/slides/{slide_index}")

    explicit = slide.get("context")
    fallback = raw.get("context")
    override = slide.get("contextOverrides")
    if explicit is not None and override is not None:
        raise _fail("E_MATERIALIZER_CONTEXT_SOURCE",
                    f"slide {slide_id}: context and contextOverrides are mutually exclusive",
                    f"/slides/{slide_index}/contextOverrides")
    if explicit is not None or (override is None and fallback is not None):
        address = explicit if explicit is not None else fallback
        try:
            source_path = resolve_store_address(manifest.path.parent, address)
        except StoreAddressError as error:
            pointer = f"/slides/{slide_index}/context" if explicit is not None else "/context"
            raise _fail("E_MATERIALIZER_PATH", f"slide {slide_id}: invalid explicit Context Store address",
                        pointer) from error
        payload, document, context_node = _parse_source(source_path, strict_manifest=False)
        origins = _origins(context_node, source_path)
        return SelectedDeckContext(document if isinstance(document, Mapping) else {}, payload,
                                   str(address), source_path, manifest.path, slide_id,
                                   "explicit", MappingProxyType(origins))

    if override is None:
        raise _fail("E_MATERIALIZER_CONTEXT_SOURCE",
                    f"slide {slide_id}: no explicit Context or Context override is declared",
                    f"/slides/{slide_index}")

    defaults = raw.get("contextDefaults")
    if not isinstance(defaults, Mapping):
        raise _fail("E_MATERIALIZER_CONTEXT_DEFAULTS",
                    f"slide {slide_id}: contextOverrides requires manifest contextDefaults",
                    f"/slides/{slide_index}/contextOverrides")
    try:
        check_store_segment(raw.get("id"))
    except StoreAddressError as error:
        raise _fail("E_MATERIALIZER_PATH", f"slide {slide_id!r}: unsafe composed Context deck id",
                    "/id") from error
    try:
        check_store_segment(slide_id)
    except StoreAddressError as error:
        raise _fail("E_MATERIALIZER_PATH", f"slide {slide_id!r}: unsafe composed Context slide id",
                    f"/slides/{slide_index}/id") from error
    override_body = override.get("body", {}) if isinstance(override, Mapping) else {}
    if override_body is None:
        override_body = {}
    if not isinstance(override_body, Mapping):
        raise _fail("E_MATERIALIZER_CONTEXT_OVERRIDE",
                    f"slide {slide_id}: contextOverrides.body must be a mapping",
                    f"/slides/{slide_index}/contextOverrides/body")
    body, origins = _compose_body(defaults, override_body, manifest, slide_index)
    document = {"version": "chrona/render-context/v0.17", "kind": "render-context",
                "id": override["id"], "body": body}
    payload = yaml.safe_dump(document, sort_keys=False, allow_unicode=True).encode("utf-8")
    address = f"_deck-contexts/{raw.get('id')}/{slide_id}.yaml"
    # The manifest id is required only for composition.
    if not isinstance(raw.get("id"), str) or not raw["id"]:
        raise _fail("E_MATERIALIZER_DECK_ID", f"slide {slide_id}: composed Context requires a manifest id",
                    f"/slides/{slide_index}/contextOverrides")
    _validate_completed_context(document, manifest, slide_index, slide_id, origins)
    return SelectedDeckContext(MappingProxyType(document), payload, address, None,
                               manifest.path, slide_id, "composed", MappingProxyType(origins))


def resolve_deck_context(manifest_path: Path, slide_id: str) -> SelectedDeckContext:
    """Load, select and compose one slide's Context source."""
    manifest = load_deck_manifest(manifest_path)
    return select_deck_context(manifest.path, manifest, slide_id)


def _compose_body(defaults: Mapping[str, Any], overrides: Mapping[str, Any],
                  manifest: DeckManifest, slide_index: int) -> tuple[dict[str, Any], dict[str, SourceOrigin]]:
    body: dict[str, Any] = {}
    origins: dict[str, SourceOrigin] = {}
    defaults_path = "/contextDefaults"
    override_path = f"/slides/{slide_index}/contextOverrides/body"
    defaults_origins = _origins(manifest.node, manifest.path)
    for key, value in defaults.items():
        if value is None:
            source_pointer = f"{defaults_path}/{key}"
            origins[f"/body/{key}"] = defaults_origins.get(source_pointer, SourceOrigin(manifest.path, source_pointer))
            continue
        body[key] = ({child: item for child, item in value.items() if item is not None}
                     if isinstance(value, Mapping) else value)
        source_pointer = f"{defaults_path}/{key}"
        origins[f"/body/{key}"] = defaults_origins.get(source_pointer, SourceOrigin(manifest.path, source_pointer))
        if isinstance(value, Mapping):
            for child, item in value.items():
                if item is None:
                    pointer = f"{source_pointer}/{child}"
                    origins[f"/body/{key}/{child}"] = defaults_origins.get(pointer, SourceOrigin(manifest.path, pointer))
                    continue
                pointer = f"{source_pointer}/{child}"
                origins[f"/body/{key}/{child}"] = defaults_origins.get(pointer, SourceOrigin(manifest.path, pointer))
    for key, value in overrides.items():
        if value is None:
            body.pop(key, None)
            _clear_origin_subtree(origins, f"/body/{key}")
            source_pointer = f"{override_path}/{key}"
            origins[f"/body/{key}"] = SourceOrigin(manifest.path, source_pointer,
                                                       locate(manifest.node, source_pointer))
            continue
        if key in {"inputs", "environment"} and isinstance(value, Mapping):
            base = dict(body.get(key, {})) if isinstance(body.get(key), Mapping) else {}
            for child, replacement in value.items():
                _clear_origin_subtree(origins, f"/body/{key}/{child}")
                child_pointer = f"{override_path}/{key}/{child}"
                if replacement is None:
                    base.pop(child, None)
                    origins[f"/body/{key}/{child}"] = SourceOrigin(
                        manifest.path, child_pointer, locate(manifest.node, child_pointer))
                else:
                    base[child] = replacement
                    origins[f"/body/{key}/{child}"] = SourceOrigin(
                        manifest.path, child_pointer, locate(manifest.node, child_pointer))
            body[key] = base
            origins[f"/body/{key}"] = SourceOrigin(manifest.path, f"{override_path}/{key}",
                                                       locate(manifest.node, f"{override_path}/{key}"))
        else:
            _clear_origin_subtree(origins, f"/body/{key}")
            body[key] = value
            source_pointer = f"{override_path}/{key}"
            origins[f"/body/{key}"] = SourceOrigin(manifest.path, source_pointer,
                                                       locate(manifest.node, source_pointer))
    return body, origins


def _clear_origin_subtree(origins: dict[str, SourceOrigin], pointer: str) -> None:
    for candidate in tuple(origins):
        if candidate == pointer or candidate.startswith(pointer + "/"):
            origins.pop(candidate, None)


def _origin_for(origins: Mapping[str, SourceOrigin], pointer: str) -> SourceOrigin | None:
    """Resolve a completed nested pointer through the most-specific authored fragment."""
    candidate = pointer
    while candidate:
        if candidate in origins:
            origin = origins[candidate]
            suffix = pointer[len(candidate):]
            return SourceOrigin(origin.path, origin.source_ref + suffix, origin.source_range)
        candidate = candidate.rpartition("/")[0]
    return None


def _validate_completed_context(document: Mapping[str, Any], manifest: DeckManifest,
                                slide_index: int, slide_id: str,
                                origins: Mapping[str, SourceOrigin]) -> None:
    # Validate fontSet-expanded data through the live immutable Context schema;
    # the payload and identity continue to reflect authored fontSet bytes.
    from chrona.presentation.contracts.font_sets import expand_font_set
    from chrona.presentation.contracts.resources import ClosureIdentity, ContractError, parse_contract

    try:
        value = expand_font_set(document)
        parse_contract(ClosureIdentity("render-context", str(document["id"]), "initialization",
                                       "sha256:" + sha256(yaml.safe_dump(document, sort_keys=False,
                                                                           allow_unicode=True).encode("utf-8")).hexdigest()),
                       value)
    except ContractError as error:
        source_ref = getattr(error, "source_ref", None) or "/body"
        origin = _origin_for(origins, source_ref)
        pointer = origin.source_ref if origin else f"/slides/{slide_index}/contextOverrides/body"
        detail = getattr(error, "detail", None) or str(error)
        raise _fail(error.diagnostic_id.partition(":")[0],
                    f"slide {slide_id}: {detail}", pointer) from error
