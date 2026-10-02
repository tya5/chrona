"""Frozen contracts constructed only after exact resource-schema acceptance."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import StrEnum
import math
import re
from typing import Any, Mapping


from chrona.core.store_address import StoreAddressError, check_store_address
from chrona.resources import schema_validator
from chrona.schema_diagnostics import SchemaViolation, explain_all_errors, explain_errors
from chrona.presentation.table_presentation import BooleanPresencePresentation


class ContractError(ValueError):
    """A decoded resource cannot become a runtime contract."""

    def __init__(self, diagnostic_id: str, detail: str = "", source_ref: str = "/") -> None:
        super().__init__(diagnostic_id)
        self.diagnostic_id = diagnostic_id
        self.detail = detail
        self.source_ref = source_ref


class UnsupportedResourceVersionError(ContractError):
    """One declared string version has no contract schema for its known kind."""

    def __init__(self, identity: ClosureIdentity, found_version: str, supported_versions: tuple[str, ...]) -> None:
        self.resource_kind = identity.kind
        self.resource_id = identity.id
        self.found_version = found_version
        self.supported_versions = supported_versions
        # Version and identity are unvalidated input at this boundary. Keep the
        # author-facing message useful without echoing an unbounded scalar.
        found = found_version if len(found_version) <= 160 else found_version[:157] + "..."
        identifier = identity.id if len(identity.id) <= 160 else identity.id[:157] + "..."
        detail = (f"{identity.kind} id={identifier} declares version {found}; "
                  f"supported: {', '.join(supported_versions)}")
        super().__init__("E_RESOURCE_VERSION_UNSUPPORTED", detail, "/version")


def _closure_kind_error(identity: ClosureIdentity, expected: str, found: object) -> ContractError:
    return ContractError("E_CLOSURE_KIND", f"resource kind={identity.kind} id={identity.id}; expected {expected}; found {type(found).__name__}")


class SchemaContractError(ContractError):
    """A supported resource has a schema-shape error at one JSON pointer."""

    def __init__(self, kind: str, source_ref: str, message: str = "invalid resource schema", violation: SchemaViolation | None = None):
        super().__init__(f"E_RESOURCE_SCHEMA: {message}")
        self.kind = kind
        self.source_ref = source_ref
        self.violation = violation


@dataclass(frozen=True)
class SchemaErrorExplanations:
    """Aggregate and legacy views of one resource validator result."""

    aggregate: tuple[SchemaViolation, ...]
    legacy: SchemaViolation
    error_count: int

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
class TableColumn:
    """One schema-accepted View table-column declaration."""

    id: str
    source: str | FrozenDict
    format: str | BooleanPresencePresentation
    missing: str
    align: str = "start"
    width: str | FrozenDict = "content"
    header_orientation: str = "horizontal"


@dataclass(frozen=True)
class ViewRowItem:
    id: str
    source_kind: str
    source_object: str
    track: str
    presentation: FrozenDict | None = None
    scenario_id: str | None = None


class ViewRowMode(StrEnum):
    """Closed row-composition vocabulary accepted by the live View contract."""

    AUTOMATIC = "automatic"
    EXPLICIT = "explicit"
    LANES = "lanes"


class ViewLaneLabel(StrEnum):
    """Meaning of the generated lane table's first column."""

    GROUP = "group"
    LANE = "lane"


class ViewTrackAllocation(StrEnum):
    """Explicit-row subtrack policy accepted by View v0.27."""

    COLLISION = "collision"


@dataclass(frozen=True)
class ViewLaneTable:
    """Finite aggregate summary intent for generated lane rows."""

    label: ViewLaneLabel
    count: bool = False


@dataclass(frozen=True)
class ViewLaneKeys:
    """View-selected Project field and object-specific explicit lane keys."""

    field: str | None = None
    by_object: FrozenDict | None = None


@dataclass(frozen=True)
class ViewRow:
    id: str
    label: str | None
    depth: int
    parent_row: str | None
    group: str | None
    table_subject: str | None
    items: tuple[ViewRowItem, ...]
    presentation: FrozenDict | None = None


@dataclass(frozen=True)
class ViewRows:
    mode: ViewRowMode
    items: tuple[ViewRow, ...]
    points: str = "attached"
    track_allocation: ViewTrackAllocation | None = None
    lane_table: ViewLaneTable | None = None
    packing: tuple[str, ...] = ()
    lane_keys: ViewLaneKeys | None = None


@dataclass(frozen=True)
class ViewSelection:
    ids: tuple[str, ...]
    types: tuple[str, ...]
    object_types: tuple[str, ...] = ()
    excluded_object_types: tuple[str, ...] = ()


@dataclass(frozen=True)
class ViewGrouping:
    by: str
    field: str | None
    order: tuple[str, ...]
    missing: str | None
    presentation: str | None
    depth: int | None
    rollup: str | None
    order_by: str | None = None


@dataclass(frozen=True)
class ViewOrdering:
    by: str
    direction: str
    tie_break: str


@dataclass(frozen=True)
class ViewWindow:
    mode: str
    start: str | None
    end: str | None
    margin_days: int


@dataclass(frozen=True)
class ViewComparison:
    baseline: str | None
    actual: str
    observation_selection: str | None
    delta_unit: str | None
    facets: tuple[str, ...]
    scenario_id: str | None = None


@dataclass(frozen=True)
class ViewVisibility:
    labels: bool | FrozenDict
    relations: str | FrozenDict
    annotations: str | FrozenDict
    fallback: FrozenDict | None = None
    links: str = "none"


@dataclass(frozen=True)
class ViewVisual:
    """Schema-accepted visual intent, without any geometry or catalog payload."""

    target_kind: str
    selector: FrozenDict
    ref: str | None
    encoding: FrozenDict | None
    side: str
    decorative: bool


@dataclass(frozen=True)
class ViewPeriod:
    """One Project period the View selects to draw; geometry and paint belong to Layout and Theme (#582)."""

    period_id: str
    label_placement: str | None = None
    label_overflow: str = "visible-overflow"


@dataclass(frozen=True)
class ViewInput:
    """Closed View v0.3 vocabulary after schema acceptance."""

    selection: ViewSelection | None
    grouping: ViewGrouping | None
    ordering: ViewOrdering | None
    window: ViewWindow
    comparison: ViewComparison
    visibility: ViewVisibility
    table_columns: tuple[TableColumn, ...]
    annotations: tuple[FrozenDict, ...]
    rows: ViewRows
    axis: FrozenDict | None
    markers: tuple[FrozenDict, ...]
    shading: FrozenDict | None
    time_presentation: FrozenDict | None
    annotation_presentation: str | None
    surface: str = "table-timeline"
    color_encoding: FrozenDict | None = None
    progress_fill: str | None = None
    visuals: tuple[ViewVisual, ...] = ()
    hierarchy_column: str | None = None
    background_decoration: tuple[str, str] = ("none", "all")
    periods: tuple[ViewPeriod, ...] = ()


@dataclass(frozen=True)
class SummaryMetric:
    id: str
    label: str
    source: str | FrozenDict
    format: str
    scope: str | None


@dataclass(frozen=True)
class SummaryPanelInput:
    id: str
    title: str | None
    presentation: str
    metrics: tuple[SummaryMetric | tuple[str, str], ...]


@dataclass(frozen=True)
class SummaryProfileInput:
    panels: tuple[SummaryPanelInput, ...]


@dataclass(frozen=True)
class LegendEntry:
    role: str
    label: str


@dataclass(frozen=True)
class ReviewDetailInput:
    group_details: tuple[FrozenDict, ...]
    milestones: tuple[str, ...]
    legend: tuple[LegendEntry, ...]
    observations: FrozenDict | None


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
    summary: SummaryProfileInput


@dataclass(frozen=True)
class ReviewDetailProfileContract(ResourceContract):
    detail: ReviewDetailInput


@dataclass(frozen=True)
class ProjectContract(ResourceContract):
    scheduler_input: FrozenDict
    extensions: tuple[FrozenDict, ...]


@dataclass(frozen=True)
class ViewContract(ResourceContract):
    view: ViewInput


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
class IconPath:
    """Renderer-neutral, importer-normalized path in a catalog entry."""

    paint: str
    data: str
    stroke_width: float | None = None
    line_cap: str | None = None
    line_join: str | None = None


_COMPACT_ARITY = {"M": 2, "L": 2, "Q": 4, "Z": 0}
_COMPACT_NUMBER = re.compile(r"-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?$")


@dataclass(frozen=True)
class CompactIconCommand:
    """Typed compact path command; avoids retaining frozen document maps at runtime."""

    kind: str
    points: tuple[tuple[float, float], ...] = ()


def _compact_commands(value: object) -> tuple[CompactIconCommand, ...]:
    """Decode the v0.3 canonical primitive stream at the contract boundary."""
    if not isinstance(value, str):
        raise ContractError("E_ICON_CATALOG_GEOMETRY")
    tokens = value.split()
    commands: list[CompactIconCommand] = []
    index = 0
    while index < len(tokens):
        kind = tokens[index]
        count = _COMPACT_ARITY.get(kind)
        if count is None or index + count >= len(tokens):
            raise ContractError("E_ICON_CATALOG_GEOMETRY")
        raw_points = tokens[index + 1:index + 1 + count]
        if any(not _COMPACT_NUMBER.fullmatch(token) for token in raw_points):
            raise ContractError("E_ICON_CATALOG_GEOMETRY")
        points = tuple(float(token) for token in raw_points)
        if not all(math.isfinite(point) for point in points):
            raise ContractError("E_ICON_CATALOG_GEOMETRY")
        commands.append(CompactIconCommand({"M": "move", "L": "line", "Q": "quadratic", "Z": "close"}[kind],
                                           tuple((points[offset], points[offset + 1])
                                                 for offset in range(0, len(points), 2))))
        index += count + 1
    if not commands or commands[0].kind != "move":
        raise ContractError("E_ICON_CATALOG_GEOMETRY")
    return tuple(commands)


@dataclass(frozen=True)
class IconRasterSource:
    """Identity-closed PNG payload retained only for a raster catalog entry."""

    address: str
    content_identity: str


@dataclass(frozen=True)
class IconEntry:
    """One canonical ``set:name`` entry, without raw SVG/XML payloads."""

    name: str
    kind: str
    viewport: tuple[int, int]
    alternative: str
    paths: tuple[IconPath, ...] = ()
    source: IconRasterSource | None = None


@dataclass(frozen=True)
class IconCatalogContract(ResourceContract):
    set_name: str
    aliases: tuple[str, ...]
    provenance: FrozenDict
    entry_aliases: FrozenDict
    entries: tuple[IconEntry, ...]
    entry_names: tuple[str, ...]
    raw_icons: FrozenDict
    raw_glyphs: FrozenDict
    raw_patterns: FrozenDict


def _check_raster_addresses(raw_icons: Mapping[str, Any]) -> None:
    """Refuse a v0.4 catalog that declares a raster ``source.address`` the shared guard refuses (#731).

    Entries are decoded lazily and schema-checked only when selected, so the schema's ``storeAddress`` alone never
    sees an entry nothing selects. Checking every declared address here keeps "the consumer refuses everything the
    schema refuses" true for the whole catalog, selected or not.
    """
    for name, entry in raw_icons.items():
        source = entry.get("source") if isinstance(entry, Mapping) else None
        if not isinstance(source, Mapping) or "address" not in source:
            continue
        try:
            check_store_address(source["address"])
        except StoreAddressError as error:
            raise ContractError("E_ICON_ASSET_PATH", f"icon {name}", f"/body/icons/{name}/source/address") from error


def _icon_catalog_contract(identity: ClosureIdentity, version: str, body: FrozenDict) -> IconCatalogContract:
    raw_icons = body["icons"]
    if not isinstance(raw_icons, FrozenDict):
        raise _closure_kind_error(identity, "icons object", raw_icons)
    aliases, provenance, entry_aliases = body["aliases"], body["provenance"], body["entryAliases"]
    if not isinstance(aliases, (FrozenList, tuple)) or not isinstance(provenance, FrozenDict) or not isinstance(entry_aliases, FrozenDict):
        raise _closure_kind_error(identity, "aliases list, provenance object, and entryAliases object", {"aliases": aliases, "provenance": provenance, "entryAliases": entry_aliases})
    raw_glyphs = body.get("glyphs", FrozenDict())
    raw_patterns = body.get("patterns", FrozenDict())
    if not isinstance(raw_glyphs, FrozenDict) or not isinstance(raw_patterns, FrozenDict):
        raise _closure_kind_error(identity, "glyphs and patterns objects", {"glyphs": raw_glyphs, "patterns": raw_patterns})
    if version == "chrona/icon-catalog/v0.4":
        _check_raster_addresses(raw_icons)
    return IconCatalogContract(identity, version, str(body["set"]), tuple(str(alias) for alias in aliases), provenance,
                               entry_aliases, (), tuple(sorted(str(name) for name in raw_icons)), raw_icons,
                               raw_glyphs, raw_patterns)


@dataclass(frozen=True)
class PresentationPresetContract(ResourceContract):
    """Validated declarative preset package; resource documents stay external."""

    package_version: str
    resources: FrozenDict
    compatible_color_schemes: tuple[FrozenDict, ...]
    preferred_visual_profile: str | None = None


@dataclass(frozen=True)
class AuthoringWorkspaceContract(ResourceContract):
    """Closed Stage-1/2 source facade, never exposed to the render pipeline."""

    project: FrozenDict
    actuals: tuple[FrozenDict, ...]
    mode: str
    binding: FrozenDict | None
    explicit_resources: FrozenDict | None
    receipt: FrozenDict | None


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
            raise ContractError("E_CLOSURE_KIND", "resource reference; expected revision object; found " + type(revision).__name__)
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
    visual_profile: str = "chrona-output/visual/v0.5-baseline"
    text_mode: str | None = None


@dataclass(frozen=True)
class TypesetterIdentity:
    engine: str
    version: str
    adapter_grammar: str


@dataclass(frozen=True)
class RenderEnvironment:
    viewport_inline: int
    viewport_block: int
    locale: str
    font_metrics: FrozenDict
    scene_precision: int
    rasterizer: FrozenDict | None
    typesetter: TypesetterIdentity | None = None

    def renderer_environment(self) -> dict[str, object]:
        return {
            "fontMetrics": self.font_metrics,
            **({"rasterizer": self.rasterizer} if self.rasterizer else {}),
            **({"typesetter": {"engine": self.typesetter.engine, "version": self.typesetter.version,
                                "adapterGrammar": self.typesetter.adapter_grammar}} if self.typesetter else {}),
        }


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
    icon_catalogs: tuple[ResourceReference, ...]
    environment: RenderEnvironment
    target: RenderTarget


@dataclass(frozen=True)
class ResolvedThemeContract:
    """The frozen derived decorative value permitted past closure resolution."""

    source_theme_id: str
    resolved_input: FrozenDict
    catalog_glyphs: FrozenDict = field(default_factory=FrozenDict)
    catalog_patterns: FrozenDict = field(default_factory=FrozenDict)


# The Render Context versions the closure and the materializer accept. v0.16 (loose Store addresses) was
# retired once every committed and packaged Context was on v0.17 (#731); it is an unsupported version now.
RENDER_CONTEXT_VERSION = "chrona/render-context/v0.17"
RENDER_CONTEXT_VERSIONS = (RENDER_CONTEXT_VERSION,)

_SCHEMAS = {
    ("render-context", "chrona/render-context/v0.17"): "render-context-v0.17.schema.yaml",
    ("project", "timeline/v0.7"): "project-v0.7.schema.yaml",
    ("view", "chrona/view/v0.26"): "view-v0.26.schema.yaml",
    ("view", "chrona/view/v0.27"): "view-v0.27.schema.yaml",
    ("view", "chrona/view/v0.28"): "view-v0.28.schema.yaml",
    ("theme", "chrona/theme/v0.11"): "theme-v0.11.schema.yaml",
    ("theme", "chrona/theme/v0.13"): "theme-v0.13.schema.yaml",
    ("theme", "chrona/theme/v0.14"): "theme-v0.14.schema.yaml",
    ("color-scheme", "chrona/color-scheme/v0.2"): "color-scheme-v0.2.schema.yaml",
    ("layout-profile", "chrona/layout-profile/v0.10"): "layout-profile-v0.10.schema.yaml",
    ("icon-catalog", "chrona/icon-catalog/v0.3"): "icon-catalog-v0.3.schema.yaml",
    ("icon-catalog", "chrona/icon-catalog/v0.4"): "icon-catalog-v0.4.schema.yaml",
    ("actual-set", "chrona/actual-set/v0.3"): "actual-set-v0.3.schema.yaml",
    ("snapshot-ref", "chrona/snapshot-ref/v0.2"): "snapshot-ref-v0.2.schema.yaml",
    ("snapshot-ref", "chrona/snapshot-ref/v0.3"): "snapshot-ref-v0.3.schema.yaml",
    ("profile-package", "chrona/profile/v0.3"): "profile-v0.3.schema.yaml",
    ("summary-profile", "chrona/summary-profile/v0.1"): "summary-profile-v0.2.schema.yaml",
    ("review-detail-profile", "chrona/review-detail-profile/v0.1"): "review-detail-profile-v0.1.schema.yaml",
    ("presentation-preset", "chrona/presentation-preset/v0.1"): "presentation-preset-v0.1.schema.yaml",
    ("authoring-workspace", "chrona/authoring-workspace/v0.1"): "authoring-workspace-v0.1.schema.yaml",
}


def _schema_for_version(identity: ClosureIdentity, version: object) -> str:
    """Select one registered schema, distinguishing stale strings from bad framing."""
    supported = tuple(sorted(candidate for kind, candidate in _SCHEMAS if kind == identity.kind))
    if not supported or not isinstance(version, str):
        raise _closure_kind_error(identity, "supported resource kind/version", version)
    schema_name = _SCHEMAS.get((identity.kind, version))
    if schema_name is None:
        raise UnsupportedResourceVersionError(identity, version, supported)
    return schema_name


def _validate(kind: str, value: Mapping[str, Any], identity: ClosureIdentity) -> str:
    version = value.get("version")
    schema_name = _schema_for_version(identity, version)
    if kind == "icon-catalog":
        body = value.get("body")
        icons = body.get("icons") if isinstance(body, Mapping) else None
        aliases = body.get("entryAliases") if isinstance(body, Mapping) else None
        if isinstance(icons, Mapping) and isinstance(aliases, Mapping):
            missing = next((name for name, target in aliases.items() if target not in icons), None)
            if missing is not None:
                raise SchemaContractError(kind, f"/body/entryAliases/{missing}", "alias target must name a canonical icon")
    candidate = _icon_catalog_envelope(value) if kind == "icon-catalog" else _schema_value(value)
    errors = tuple(schema_validator(schema_name).iter_errors(candidate))
    if errors:
        violation = explain_errors(errors, resource_kind=kind, resource_identity=identity.id)
        raise SchemaContractError(kind, violation.pointer, violation.message, violation)
    return version


def explain_schema_errors(identity: ClosureIdentity, value: Mapping[str, Any]) -> tuple[SchemaViolation, ...]:
    """Explain every resource-schema error without constructing a contract.

    The single-error ``_validate`` path remains the compatibility boundary for
    existing callers.  Presentation ingress collection uses this separate
    function before it decides whether a resource is safe to parse.
    """
    report = explain_resource_schema_errors(identity, value)
    return report.aggregate if report is not None else ()


def explain_resource_schema_errors(identity: ClosureIdentity, value: Mapping[str, Any]) -> SchemaErrorExplanations | None:
    """Return aggregate and legacy explanations for one resource, if invalid."""
    errors = _resource_schema_errors(identity, value)
    if not errors:
        return None
    return SchemaErrorExplanations(
        explain_all_errors(errors, resource_kind=identity.kind, resource_identity=identity.id),
        explain_errors(errors, resource_kind=identity.kind, resource_identity=identity.id),
        len(errors),
    )
def _resource_schema_errors(identity: ClosureIdentity, value: Mapping[str, Any]) -> tuple[ValidationError, ...]:
    """Evaluate one resource schema without constructing a runtime contract."""
    version = value.get("version")
    schema_name = _schema_for_version(identity, version)
    candidate = _icon_catalog_envelope(value) if identity.kind == "icon-catalog" else _schema_value(value)
    return tuple(schema_validator(schema_name).iter_errors(candidate))


def _icon_catalog_envelope(value: Mapping[str, Any]) -> dict[str, Any]:
    """Validate catalog framing without paying to decode every unselected icon."""
    body = value.get("body")
    icons = body.get("icons") if isinstance(body, dict) else None
    if not isinstance(icons, dict):
        return _schema_value(value)
    entry_aliases = body.get("entryAliases")
    name = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]*$")
    if (not all(isinstance(key, str) and name.fullmatch(key) and isinstance(entry, Mapping)
                for key, entry in icons.items())
            or not isinstance(entry_aliases, dict)
            or not all(isinstance(key, str) and name.fullmatch(key)
                       and isinstance(target, str) and name.fullmatch(target)
                       for key, target in entry_aliases.items())):
        # Keep the malformed map intact so normal schema diagnostics describe it.
        return _schema_value(value)
    # The schema validates the map's entry shape through one representative;
    # every selected entry is validated independently before it reaches Scene.
    name, entry = next(iter(icons.items())) if icons else (None, None)
    envelope = dict(value)
    envelope_body = dict(body)
    envelope_body["icons"] = {name: entry} if name is not None else {}
    if value.get("version") == "chrona/icon-catalog/v0.4":
        for collection in ("glyphs", "patterns"):
            entries = body.get(collection)
            if not isinstance(entries, dict):
                return _schema_value(value)
            if entries:
                key, item = next(iter(entries.items()))
                envelope_body[collection] = {key: item}
    envelope["body"] = envelope_body
    return _schema_value(envelope)


def validate_icon_catalog_entry(catalog: IconCatalogContract, name: str) -> None:
    """Schema-check one selected raw entry, then let closure expand its commands."""
    raw = catalog.raw_icons.get(name)
    if raw is None:
        raise ContractError("E_ICON_CATALOG_SCHEMA")
    source = {
        "version": catalog.version, "kind": "icon-catalog", "id": catalog.identity.id,
        "body": {"set": catalog.set_name, "aliases": list(catalog.aliases),
                 "provenance": dict(catalog.provenance), "entryAliases": dict(catalog.entry_aliases),
                 **({"glyphs": dict(catalog.raw_glyphs), "patterns": dict(catalog.raw_patterns)}
                    if catalog.version == "chrona/icon-catalog/v0.4" else {}),
                 "icons": {name: raw}},
    }
    errors = tuple(schema_validator(_SCHEMAS[("icon-catalog", catalog.version)]).iter_errors(_schema_value(source)))
    if errors:
        violation = explain_errors(errors, resource_kind="icon-catalog", resource_identity=catalog.identity.id)
        raise SchemaContractError("icon-catalog", violation.pointer, violation.message, violation)


def validate_theme_asset_entry(catalog: IconCatalogContract, asset_kind: str, name: str) -> Any:
    """Schema-check one selected normalized glyph or pattern entry."""
    collection = {"glyph": catalog.raw_glyphs, "pattern": catalog.raw_patterns}.get(asset_kind)
    if catalog.version != "chrona/icon-catalog/v0.4" or collection is None:
        raise ContractError("E_THEME_ASSET_REFERENCE")
    raw = collection.get(name)
    if raw is None:
        raise ContractError("E_THEME_ASSET_REFERENCE")
    source = {
        "version": catalog.version, "kind": "icon-catalog", "id": catalog.identity.id,
        "body": {"set": catalog.set_name, "aliases": list(catalog.aliases),
                 "provenance": dict(catalog.provenance), "entryAliases": dict(catalog.entry_aliases),
                 "icons": {}, "glyphs": {name: raw} if asset_kind == "glyph" else {},
                 "patterns": {name: raw} if asset_kind == "pattern" else {}},
    }
    errors = tuple(schema_validator(_SCHEMAS[("icon-catalog", catalog.version)]).iter_errors(_schema_value(source)))
    if errors:
        violation = explain_errors(errors, resource_kind="icon-catalog", resource_identity=catalog.identity.id)
        raise SchemaContractError("icon-catalog", violation.pointer, violation.message, violation)
    return raw


def _schema_value(value: Any) -> Any:
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Mapping):
        return {key: _schema_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_schema_value(item) for item in value]
    return value


def _view_input(body: FrozenDict, version: str) -> ViewInput:
    rows = body["rows"]
    raw_selection = body.get("selection", FrozenDict())
    raw_include = raw_selection.get("include", FrozenDict())
    raw_exclude = raw_selection.get("exclude", FrozenDict())
    selection = ViewSelection(tuple(str(item) for item in raw_include.get("ids", ())),
                              tuple(str(item) for item in raw_include.get("types", ())),
                              tuple(str(item) for item in raw_include.get("objectTypes", ())),
                              tuple(str(item) for item in raw_exclude.get("objectTypes", ()))) if raw_selection else None
    raw_grouping = body.get("grouping")
    grouping = (ViewGrouping(str(raw_grouping["by"]), str(raw_grouping["field"]) if "field" in raw_grouping else None,
                             tuple(str(item) for item in raw_grouping.get("order", ()))
                             if not isinstance(raw_grouping.get("order"), FrozenDict) else (),
                             str(raw_grouping["missing"]) if "missing" in raw_grouping else None,
                             str(raw_grouping["presentation"]) if "presentation" in raw_grouping else None,
                             int(raw_grouping["depth"]) if "depth" in raw_grouping else None,
                             str(raw_grouping["rollup"]) if "rollup" in raw_grouping else None,
                             str(raw_grouping["order"]["by"]) if isinstance(raw_grouping.get("order"), FrozenDict) else None)
                if raw_grouping else None)
    raw_ordering = body.get("ordering")
    ordering = (ViewOrdering(str(raw_ordering["by"]), str(raw_ordering["direction"]), str(raw_ordering["tieBreak"]))
                if raw_ordering else None)
    raw_window = body["window"]
    window = ViewWindow(str(raw_window["mode"]), str(raw_window["start"]) if "start" in raw_window else None,
                        str(raw_window["end"]) if "end" in raw_window else None, int(raw_window.get("marginDays", 0)))
    raw_comparison = body["comparison"]
    comparison = ViewComparison(str(raw_comparison["baseline"]) if "baseline" in raw_comparison else None,
                                str(raw_comparison["actual"]),
                                str(raw_comparison["observationSelection"]) if "observationSelection" in raw_comparison else None,
                                str(raw_comparison["deltaUnit"]) if "deltaUnit" in raw_comparison else None,
                                tuple(str(item) for item in raw_comparison.get("facets", ())),
                                str(raw_comparison["scenario"]) if "scenario" in raw_comparison else None)
    raw_visibility = body["visibility"]
    _validate_view_fallback(raw_visibility.get("fallback"))
    visibility = ViewVisibility(raw_visibility["labels"], raw_visibility["relations"], raw_visibility["annotations"],
                                raw_visibility.get("fallback"), str(raw_visibility.get("links", "none")))
    row_items = tuple(
        ViewRow(str(row["id"]), str(row["label"]) if "label" in row else None, int(row["depth"]),
                str(row["parentRow"]) if "parentRow" in row else None,
                str(row["group"]) if "group" in row else None,
                str(row["tableSubject"]) if "tableSubject" in row else None,
                tuple(ViewRowItem(str(item["id"]), str(item["source"]["kind"]),
                                  str(item["source"]["object"]), str(item.get("track", "stacked")), item.get("presentation"),
                                  str(item["source"]["scenario"]) if "scenario" in item["source"] else None)
                      for item in row.get("items", ())), row.get("presentation"))
        for row in rows.get("items", ()))
    table_columns = tuple(TableColumn(str(column["id"]), column["source"], _table_format(column.get("format", "text")),
                                      str(column["missing"]), str(column["align"]), column["width"],
                                      str(column["headerOrientation"]))
                          for column in body.get("tableColumns", ()))
    hierarchy_column = str(body["hierarchyColumn"]) if "hierarchyColumn" in body else None
    _validate_view_table_intent(table_columns, grouping, row_items, hierarchy_column)
    labels = visibility.labels
    if (isinstance(labels, Mapping) and labels.get("placement") == "both"
            and not any(column.source == "title" for column in table_columns)):
        raise ContractError("E_VIEW_LABELS_BOTH_TABLE_TITLE")
    return ViewInput(
        selection, grouping, ordering, window, comparison, visibility,
        table_columns,
        tuple(body.get("annotations", ())), ViewRows(
            ViewRowMode(str(rows["mode"])), row_items, str(rows.get("points", "attached")),
            ViewTrackAllocation(str(rows["trackAllocation"])) if "trackAllocation" in rows else None,
            (ViewLaneTable(ViewLaneLabel(str(rows["laneTable"]["label"])), bool(rows["laneTable"].get("count", False)))
             if "laneTable" in rows else None),
            (tuple(str(item) for item in rows.get("packing", ("explicit", "attached")))
             if version == "chrona/view/v0.28" else ()),
            (ViewLaneKeys(str(rows["laneKeys"]["field"]) if "field" in rows["laneKeys"] else None,
                          rows["laneKeys"].get("byObject"))
             if version == "chrona/view/v0.28" and "laneKeys" in rows else None),
        ), body.get("axis"),
        tuple(body.get("markers", ())), body.get("shading"), body.get("timePresentation"),
        str(body["annotationPresentation"]) if "annotationPresentation" in body else None,
        str(body["surface"]), body.get("colorEncoding"),
        str(body["progressFill"]["source"]) if "progressFill" in body else None,
        tuple(ViewVisual(str(item["target"]["kind"]), item["target"], str(item["ref"]) if "ref" in item else None,
                         item.get("encoding"), str(item.get("side", "leading")), bool(item.get("decorative", True)))
              for item in body.get("visuals", ())),
        hierarchy_column=hierarchy_column,
        background_decoration=(str(body.get("backgroundDecoration", FrozenDict()).get("rows", "none")),
                               str(body.get("backgroundDecoration", FrozenDict()).get("groups", "all"))),
        periods=_view_periods(body.get("periods", ())))


def _view_periods(raw: Any) -> tuple[ViewPeriod, ...]:
    """Close the schema-accepted period selection; one entry per Project period (#582)."""
    periods = tuple(ViewPeriod(str(item["id"]),
                               str(item["label"]["placement"]) if "label" in item else None,
                               str(item["label"].get("overflow", "visible-overflow")) if "label" in item else "visible-overflow")
                    for item in raw)
    if len({item.period_id for item in periods}) != len(periods):
        raise ContractError("E_VIEW_PERIOD_DUPLICATE")
    return periods


def _validate_view_table_intent(table_columns: tuple[TableColumn, ...], grouping: ViewGrouping | None,
                                rows: tuple[ViewRow, ...], hierarchy_column: str | None) -> None:
    """Reject View composition ambiguities before Layout measures them."""
    column_ids = tuple(column.id for column in table_columns)
    if len(set(column_ids)) != len(column_ids):
        raise ContractError("E_VIEW_TABLE_COLUMN_DUPLICATE")
    for column in table_columns:
        if (isinstance(column.source, Mapping) and column.source.get("comparisonFacet") == "missingActual"
                and not isinstance(column.format, BooleanPresencePresentation)):
            raise ContractError("E_VIEW_BOOLEAN_PRESENTATION")
    visible_nesting = ((grouping is not None and grouping.by == "hierarchy")
                       or any(row.depth > 0 or row.parent_row is not None for row in rows))
    if hierarchy_column is None:
        if visible_nesting:
            raise ContractError("E_VIEW_HIERARCHY_COLUMN_REQUIRED")
        return
    if hierarchy_column not in column_ids:
        raise ContractError("E_VIEW_HIERARCHY_COLUMN_UNKNOWN")
    if not visible_nesting:
        raise ContractError("E_VIEW_HIERARCHY_COLUMN_UNEXPECTED")


def _table_format(value: object) -> str | BooleanPresencePresentation:
    """Close the schema-approved formatter before content normalization."""
    if isinstance(value, Mapping):
        if value.get("kind") == "presence" and isinstance(value.get("whenTrue"), str) and isinstance(value.get("whenFalse"), str):
            return BooleanPresencePresentation(value["whenTrue"], value["whenFalse"])
        raise ContractError("E_VIEW_BOOLEAN_PRESENTATION")
    if isinstance(value, str):
        return value
    raise ContractError("E_VIEW_BOOLEAN_PRESENTATION")


def _validate_view_fallback(raw_fallback: Any) -> None:
    """Reject non-operational preference ladders at the typed View boundary."""
    if not isinstance(raw_fallback, Mapping):
        return
    allowed = {
        "labels": {"above", "below", "start", "end", "inside", "suppress"},
        "annotations": {"above", "below", "start", "end", "rail", "suppress"},
    }
    for name, vocabulary in allowed.items():
        if name not in raw_fallback:
            continue
        ladder = tuple(str(item) for item in raw_fallback[name])
        if (not ladder or len(set(ladder)) != len(ladder) or any(item not in vocabulary for item in ladder)
                or ("suppress" in ladder and ladder[-1] != "suppress")
                or all(item == "suppress" for item in ladder)):
            raise ValueError(f"E_VIEW_FALLBACK_INVALID:{name}")


def _summary_input(body: FrozenDict) -> SummaryProfileInput:
    panels: list[SummaryPanelInput] = []
    for panel in body["panels"]:
        declared = panel["metrics"]
        entries = declared.items() if isinstance(declared, FrozenDict) else ((item["id"], item) for item in declared)
        metrics: list[SummaryMetric | tuple[str, str]] = []
        for metric_id, definition in entries:
            if isinstance(definition, FrozenDict):
                metrics.append(SummaryMetric(str(metric_id), str(definition.get("label", metric_id)), definition["source"],
                                             str(definition["format"]), str(definition["scope"]) if "scope" in definition else None))
            else:
                metrics.append((str(metric_id), str(definition)))
        panels.append(SummaryPanelInput(str(panel["id"]), str(panel["title"]) if "title" in panel else None,
                                        str(panel.get("presentation", "lines")), tuple(metrics)))
    return SummaryProfileInput(tuple(panels))


def _review_detail_input(body: FrozenDict) -> ReviewDetailInput:
    return ReviewDetailInput(tuple(body.get("groupDetails", ())), tuple(str(item) for item in body.get("milestones", ())),
                             tuple(LegendEntry(str(item["role"]), str(item["label"])) for item in body.get("legend", ())),
                             body.get("observations"))


def parse_contract(identity: ClosureIdentity, value: Mapping[str, Any]) -> ResourceContract:
    """Validate an exact schema then construct its frozen, kind-specific contract."""
    frozen = freeze(value)
    body = frozen.get("body", FrozenDict())
    if not isinstance(body, FrozenDict):
        raise _closure_kind_error(identity, "resource body object", body)
    version = _validate(identity.kind, value, identity)
    if identity.kind == "project":
        extensions = frozen.get("extensions", ())
        if not isinstance(extensions, (tuple, FrozenList)) or not all(isinstance(item, FrozenDict) for item in extensions):
            raise _closure_kind_error(identity, "extension object list", extensions)
        return ProjectContract(identity, version, frozen, tuple(extensions))
    if identity.kind == "view":
        return ViewContract(identity, version, _view_input(body, version))
    if identity.kind == "theme":
        return ThemeContract(identity, version, frozen)
    if identity.kind == "color-scheme":
        return ColorSchemeContract(identity, version, frozen)
    if identity.kind == "layout-profile":
        return LayoutProfileContract(identity, version, frozen)
    if identity.kind == "icon-catalog":
        return _icon_catalog_contract(identity, version, body)
    if identity.kind == "render-context":
        inputs, environment, target = body["inputs"], body["environment"], body["target"]
        if not all(isinstance(item, FrozenDict) for item in (inputs, environment, target)):
            raise _closure_kind_error(identity, "inputs, environment, and target objects", {"inputs": inputs, "environment": environment, "target": target})
        viewport = environment["viewport"]
        if not isinstance(viewport, FrozenDict):
            raise _closure_kind_error(identity, "viewport object", viewport)
        rasterizer = environment.get("rasterizer")
        if rasterizer is not None and not isinstance(rasterizer, FrozenDict):
            raise _closure_kind_error(identity, "rasterizer object or absent", rasterizer)
        raw_typesetter = environment.get("typesetter")
        if raw_typesetter is not None and not isinstance(raw_typesetter, FrozenDict):
            raise _closure_kind_error(identity, "typesetter object or absent", raw_typesetter)
        typesetter = (TypesetterIdentity(str(raw_typesetter["engine"]), str(raw_typesetter["version"]),
                                         str(raw_typesetter["adapterGrammar"])) if raw_typesetter else None)
        return RenderContextContract(
            identity, version,
            ResourceReference.from_value(body["project"]), ResourceReference.from_value(body["view"]),
            ResourceReference.from_value(body["theme"]), ResourceReference.from_value(body["colorScheme"]),
            ResourceReference.from_value(body["layout"]),
            ResourceReference.from_value(inputs["actual"]) if "actual" in inputs else None,
            ResourceReference.from_value(inputs["snapshot"]) if "snapshot" in inputs else None,
            ResourceReference.from_value(inputs["summaryProfile"]) if "summaryProfile" in inputs else None,
            ResourceReference.from_value(inputs["detailProfile"]) if "detailProfile" in inputs else None,
            tuple(ResourceReference.from_value(item) for item in inputs.get("iconCatalogs", ())),
            RenderEnvironment(int(viewport["inlineSize"]), int(viewport["blockSize"]), str(environment["locale"]),
                              environment["fontMetrics"], int(environment["scenePrecision"]), rasterizer, typesetter),
            RenderTarget(str(target["kind"]), tuple(str(item) for item in target["capabilities"]), str(target["visualProfile"]),
                         str(target["textMode"]) if "textMode" in target else None),
        )
    if identity.kind == "actual-set":
        return ActualSetContract(identity, version, frozen)
    if identity.kind == "snapshot-ref":
        return SnapshotRefContract(identity, version, ResourceReference.from_value(body["project"]))
    if identity.kind == "profile-package":
        return ProfilePackageContract(identity, version, str(frozen["packageId"]), frozen)
    if identity.kind == "summary-profile":
        return SummaryProfileContract(identity, version, _summary_input(body))
    if identity.kind == "review-detail-profile":
        return ReviewDetailProfileContract(identity, version, _review_detail_input(body))
    if identity.kind == "presentation-preset":
        package, resources, schemes = body["package"], body["resources"], body["compatibleColorSchemes"]
        if not isinstance(package, FrozenDict):
            raise _closure_kind_error(identity, "preset package object", package)
        if not isinstance(resources, FrozenDict):
            raise _closure_kind_error(identity, "preset resources object", resources)
        if not isinstance(schemes, (FrozenList, tuple)) or not all(isinstance(item, FrozenDict) for item in schemes):
            raise _closure_kind_error(identity, "preset compatible color-scheme object list", schemes)
        preference = body.get("visualProfile")
        preferred = str(preference["preferred"]) if isinstance(preference, FrozenDict) else None
        return PresentationPresetContract(identity, version, str(package["version"]), resources, tuple(schemes), preferred)
    if identity.kind == "authoring-workspace":
        project, presentation = body["project"], body["presentation"]
        actuals = body.get("actuals", ())
        if not isinstance(project, FrozenDict):
            raise _closure_kind_error(identity, "workspace project object", project)
        if not isinstance(presentation, FrozenDict):
            raise _closure_kind_error(identity, "workspace presentation object", presentation)
        if not isinstance(actuals, (FrozenList, tuple)) or not all(isinstance(item, FrozenDict) for item in actuals):
            raise _closure_kind_error(identity, "workspace actual object list", actuals)
        mode = str(presentation["mode"])
        binding = presentation.get("binding")
        resources = presentation.get("resources")
        receipt = presentation.get("receipt")
        if mode == "guided" and not isinstance(binding, FrozenDict):
            raise _closure_kind_error(identity, "guided workspace binding object", binding)
        if mode == "explicit" and not isinstance(resources, FrozenDict):
            raise _closure_kind_error(identity, "explicit workspace resources object", resources)
        if mode == "explicit" and not isinstance(receipt, FrozenDict):
            raise _closure_kind_error(identity, "explicit workspace receipt object", receipt)
        _validate_workspace_identifiers(identity, project, actuals)
        return AuthoringWorkspaceContract(identity, version, project, tuple(actuals), mode,
                                         binding if isinstance(binding, FrozenDict) else None,
                                         resources if isinstance(resources, FrozenDict) else None,
                                         receipt if isinstance(receipt, FrozenDict) else None)
    raise ContractError("E_CLOSURE_KIND", f"resource kind={identity.kind} id={identity.id}; expected supported resource contract kind; found unsupported kind={identity.kind}")


def _validate_workspace_identifiers(identity: ClosureIdentity, project: FrozenDict,
                                    actuals: FrozenList | tuple[Any, ...]) -> None:
    tasks = project.get("tasks", ())
    if not isinstance(tasks, (FrozenList, tuple)):
        raise _closure_kind_error(identity, "workspace task object list", tasks)
    task_ids = tuple(str(task["id"]) for task in tasks if isinstance(task, FrozenDict))
    if len(task_ids) != len(tasks) or len(task_ids) != len(set(task_ids)):
        raise ContractError("E_AUTHORING_TASK_ID")
    actual_ids = tuple(str(item["taskId"]) for item in actuals)
    if len(actual_ids) != len(set(actual_ids)) or any(task_id not in task_ids for task_id in actual_ids):
        raise ContractError("E_AUTHORING_ACTUAL_TASK")
