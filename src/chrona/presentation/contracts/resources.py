"""Frozen contracts constructed only after exact resource-schema acceptance."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any, Iterable, Mapping

import jsonschema
import yaml
from referencing import Registry, Resource

from chrona.resources import schema_resource


class ContractError(ValueError):
    """A decoded resource cannot become a runtime contract."""


class SchemaContractError(ContractError):
    """A supported resource has a schema-shape error at one JSON pointer."""

    def __init__(self, kind: str, source_ref: str):
        super().__init__("E_RESOURCE_SCHEMA")
        self.kind = kind
        self.source_ref = source_ref

class FrozenDict(dict[str, Any]):
    """A dict-compatible value that rejects all mutation after closure parsing."""

    @staticmethod
    def _immutable(*_args: Any, **_kwargs: Any) -> None:
        raise TypeError("presentation contract values are immutable")

    __setitem__ = _immutable
    __delitem__ = _immutable
    clear = _immutable
    pop = _immutable
    popitem = _immutable
    setdefault = _immutable
    update = _immutable

    def __deepcopy__(self, memo: dict[int, Any]) -> dict[str, Any]:
        from copy import deepcopy
        return {key: deepcopy(value, memo) for key, value in self.items()}


class FrozenList(list[Any]):
    """A list-compatible value that rejects all mutation after closure parsing."""

    @staticmethod
    def _immutable(*_args: Any, **_kwargs: Any) -> None:
        raise TypeError("presentation contract values are immutable")

    __setitem__ = _immutable
    __delitem__ = _immutable
    __iadd__ = _immutable
    __imul__ = _immutable
    append = _immutable
    clear = _immutable
    extend = _immutable
    insert = _immutable
    pop = _immutable
    remove = _immutable
    reverse = _immutable
    sort = _immutable

    def __deepcopy__(self, memo: dict[int, Any]) -> list[Any]:
        from copy import deepcopy
        return [deepcopy(value, memo) for value in self]


def freeze(value: Any) -> Any:
    """Recursively detach decoded YAML from its immutable contract representation."""
    if isinstance(value, Mapping):
        result = FrozenDict()
        dict.update(result, {str(key): freeze(item) for key, item in value.items()})
        return result
    if isinstance(value, list):
        result = FrozenList()
        list.extend(result, (freeze(item) for item in value))
        return result
    if isinstance(value, tuple):
        return tuple(freeze(item) for item in value)
    return value


@dataclass(frozen=True)
class ClosureIdentity:
    kind: str
    id: str
    revision: str
    content_identity: str


@dataclass(frozen=True)
class ResourceContract:
    """Typed resource envelope; subclasses name the owning contract kind."""

    identity: ClosureIdentity
    version: str


@dataclass(frozen=True)
class ActualSetContract(ResourceContract):
    observations_input: FrozenDict


@dataclass(frozen=True)
class SnapshotRefContract(ResourceContract):
    project: ResourceReference


@dataclass(frozen=True)
class ProfilePackageContract(ResourceContract):
    package_id: str
    profile_input: FrozenDict


@dataclass(frozen=True)
class SummaryProfileContract(ResourceContract):
    summary_input: FrozenDict


@dataclass(frozen=True)
class ReviewDetailProfileContract(ResourceContract):
    detail_input: FrozenDict


@dataclass(frozen=True)
class ProjectContract(ResourceContract):
    scheduler_input: FrozenDict
    extensions: tuple[FrozenDict, ...]


@dataclass(frozen=True)
class ViewContract(ResourceContract):
    projection_input: FrozenDict


@dataclass(frozen=True)
class ThemeContract(ResourceContract):
    theme_input: FrozenDict


@dataclass(frozen=True)
class ColorSchemeContract(ResourceContract):
    scheme_input: FrozenDict


@dataclass(frozen=True)
class LayoutProfileContract(ResourceContract):
    layout_input: FrozenDict


@dataclass(frozen=True)
class ResourceReference:
    """One immutable Context edge, decoded after Context schema acceptance."""

    id: str
    kind: str
    store: FrozenDict
    address: str
    revision_token: str
    content_identity: str | None

    @classmethod
    def from_value(cls, value: FrozenDict) -> "ResourceReference":
        revision = value["revision"]
        if not isinstance(revision, FrozenDict):
            raise ContractError("E_CLOSURE_KIND")
        return cls(str(value["id"]), str(value["kind"]), value["store"], str(value["address"]),
                   str(revision["token"]), value.get("contentIdentity"))

    def as_reader_reference(self) -> FrozenDict:
        return freeze({"id": self.id, "kind": self.kind, "store": self.store,
                       "address": self.address, "revision": {"token": self.revision_token},
                       **({"contentIdentity": self.content_identity} if self.content_identity else {})})


@dataclass(frozen=True)
class RenderTarget:
    kind: str
    capabilities: tuple[str, ...]


@dataclass(frozen=True)
class RenderEnvironment:
    viewport_inline: int
    viewport_block: int
    locale: str
    font_metrics: FrozenDict
    scene_precision: int
    rasterizer: FrozenDict | None


@dataclass(frozen=True)
class RenderContextContract(ResourceContract):
    project: ResourceReference
    view: ResourceReference
    theme: ResourceReference
    color_scheme: ResourceReference
    layout: ResourceReference
    actual: ResourceReference | None
    snapshot: ResourceReference | None
    summary_profile: ResourceReference | None
    detail_profile: ResourceReference | None
    environment: RenderEnvironment
    target: RenderTarget


@dataclass(frozen=True)
class ResolvedThemeContract:
    """The frozen derived decorative value permitted past closure resolution."""

    source_theme_id: str
    resolved_input: FrozenDict


_SCHEMAS = {
    ("render-context", "chrona/render-context/v0.7"): "render-context-v0.7.schema.yaml",
    ("project", "timeline/v0.3"): "project-v0.3.schema.yaml",
    ("view", "chrona/view/v0.1"): "view-v0.1.schema.yaml",
    ("view", "chrona/view/v0.2"): "view-v0.2.schema.yaml",
    ("theme", "chrona/theme/v0.2"): "theme-v0.2.schema.yaml",
    ("color-scheme", "chrona/color-scheme/v0.1"): "color-scheme-v0.1.schema.yaml",
    ("layout-profile", "chrona/layout-profile/v0.2"): "layout-profile-v0.2.schema.yaml",
    ("actual-set", "chrona/actual-set/v0.1"): "actual-set-v0.1.schema.yaml",
    ("actual-set", "chrona/actual-set/v0.2"): "actual-set-v0.2.schema.yaml",
    ("snapshot-ref", "chrona/snapshot-ref/v0.2"): "snapshot-ref-v0.2.schema.yaml",
    ("profile-package", "chrona/profile/v0.1"): "profile-v0.1.schema.yaml",
    ("summary-profile", "chrona/summary-profile/v0.1"): "summary-profile-v0.2.schema.yaml",
    ("review-detail-profile", "chrona/review-detail-profile/v0.1"): "review-detail-profile-v0.1.schema.yaml",
}


def _registry() -> Registry:
    names = ("presentation-resource-v0.1.schema.yaml", "revision-store-resource-ref-v0.1.schema.yaml")
    registry = Registry()
    for name in names:
        schema = yaml.safe_load(schema_resource(name).read_text(encoding="utf-8"))
        registry = registry.with_resource(schema["$id"], Resource.from_contents(schema))
    return registry


def _validate(kind: str, value: Mapping[str, Any]) -> str:
    version = value.get("version")
    schema_name = _SCHEMAS.get((kind, version)) if isinstance(version, str) else None
    if schema_name is None:
        raise ContractError("E_CLOSURE_KIND")
    schema = yaml.safe_load(schema_resource(schema_name).read_text(encoding="utf-8"))
    errors = tuple(jsonschema.Draft202012Validator(schema, registry=_registry()).iter_errors(_schema_value(value)))
    if errors:
        error = min(errors, key=lambda item: (_json_pointer(item.absolute_path), item.message))
        raise SchemaContractError(kind, _json_pointer(error.absolute_path))
    return version


def _json_pointer(path: Iterable[Any]) -> str:
    """Encode a jsonschema path as an RFC 6901 pointer."""
    parts = tuple(str(item).replace("~", "~0").replace("/", "~1") for item in path)
    return "/" + "/".join(parts) if parts else "/"


def _schema_value(value: Any) -> Any:
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Mapping):
        return {key: _schema_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_schema_value(item) for item in value]
    return value


def parse_contract(identity: ClosureIdentity, value: Mapping[str, Any]) -> ResourceContract:
    """Validate an exact schema then construct its frozen, kind-specific contract."""
    frozen = freeze(value)
    body = frozen.get("body", FrozenDict())
    if not isinstance(body, FrozenDict):
        raise ContractError("E_CLOSURE_KIND")
    version = _validate(identity.kind, value)
    if identity.kind == "project":
        extensions = frozen.get("extensions", ())
        if not isinstance(extensions, (tuple, FrozenList)) or not all(isinstance(item, FrozenDict) for item in extensions):
            raise ContractError("E_CLOSURE_KIND")
        return ProjectContract(identity, version, frozen, tuple(extensions))
    if identity.kind == "view":
        return ViewContract(identity, version, frozen)
    if identity.kind == "theme":
        return ThemeContract(identity, version, frozen)
    if identity.kind == "color-scheme":
        return ColorSchemeContract(identity, version, frozen)
    if identity.kind == "layout-profile":
        return LayoutProfileContract(identity, version, frozen)
    if identity.kind == "render-context":
        inputs, environment, target = body["inputs"], body["environment"], body["target"]
        if not all(isinstance(item, FrozenDict) for item in (inputs, environment, target)):
            raise ContractError("E_CLOSURE_KIND")
        viewport = environment["viewport"]
        if not isinstance(viewport, FrozenDict):
            raise ContractError("E_CLOSURE_KIND")
        rasterizer = environment.get("rasterizer")
        if rasterizer is not None and not isinstance(rasterizer, FrozenDict):
            raise ContractError("E_CLOSURE_KIND")
        return RenderContextContract(
            identity, version,
            ResourceReference.from_value(body["project"]), ResourceReference.from_value(body["view"]),
            ResourceReference.from_value(body["theme"]), ResourceReference.from_value(body["colorScheme"]),
            ResourceReference.from_value(body["layout"]),
            ResourceReference.from_value(inputs["actual"]) if "actual" in inputs else None,
            ResourceReference.from_value(inputs["snapshot"]) if "snapshot" in inputs else None,
            ResourceReference.from_value(inputs["summaryProfile"]) if "summaryProfile" in inputs else None,
            ResourceReference.from_value(inputs["detailProfile"]) if "detailProfile" in inputs else None,
            RenderEnvironment(int(viewport["inlineSize"]), int(viewport["blockSize"]), str(environment["locale"]),
                              environment["fontMetrics"], int(environment["scenePrecision"]), rasterizer),
            RenderTarget(str(target["kind"]), tuple(str(item) for item in target["capabilities"])),
        )
    if identity.kind == "actual-set":
        return ActualSetContract(identity, version, frozen)
    if identity.kind == "snapshot-ref":
        return SnapshotRefContract(identity, version, ResourceReference.from_value(body["project"]))
    if identity.kind == "profile-package":
        return ProfilePackageContract(identity, version, str(frozen["packageId"]), frozen)
    if identity.kind == "summary-profile":
        return SummaryProfileContract(identity, version, frozen)
    if identity.kind == "review-detail-profile":
        return ReviewDetailProfileContract(identity, version, frozen)
    raise ContractError("E_CLOSURE_KIND")
