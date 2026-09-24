"""Frozen contracts constructed only after exact resource-schema acceptance."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from functools import cache
from hashlib import sha256
from importlib.resources import files
import json
import math
import re
from typing import Any, Mapping

import jsonschema
from referencing import Registry, Resource

from chrona.resources import schema_document
from chrona.schema_diagnostics import SchemaViolation, explain_errors


class ContractError(ValueError):
    """A decoded resource cannot become a runtime contract."""


class SchemaContractError(ContractError):
    """A supported resource has a schema-shape error at one JSON pointer."""

    def __init__(self, kind: str, source_ref: str, message: str = "invalid resource schema", violation: SchemaViolation | None = None):
        super().__init__(f"E_RESOURCE_SCHEMA: {message}")
        self.kind = kind
        self.source_ref = source_ref
        self.violation = violation

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
    format: str
    missing: str


@dataclass(frozen=True)
class ViewRowItem:
    id: str
    source_kind: str
    source_object: str
    track: str
    presentation: FrozenDict | None = None
    scenario_id: str | None = None


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
    mode: str
    items: tuple[ViewRow, ...]
    points: str = "own-row"


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
class ViewInput:
    """Closed View v0.3 vocabulary after schema acceptance."""

    selection: ViewSelection | None
    grouping: ViewGrouping | None
    ordering: ViewOrdering | None
    window: ViewWindow
    comparison: ViewComparison
    visibility: ViewVisibility
    layout_intent: FrozenDict
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
    entry_names: tuple[str, ...] = ()
    projected_icons: FrozenDict | None = None


_MATERIAL_PROJECTION = "icons/material-symbols-outline-rounded-v2026-09-22.projection.json"


def _icon_catalog_contract(identity: ClosureIdentity, version: str, body: FrozenDict, *, validate_geometry: bool) -> IconCatalogContract:
    raw_icons = body["icons"]
    if not isinstance(raw_icons, FrozenDict):
        raise ContractError("E_CLOSURE_KIND")
    entries: list[IconEntry] = []
    for name, raw in sorted(raw_icons.items()):
        if not isinstance(raw, FrozenDict) or not isinstance(raw.get("viewport"), FrozenDict):
            raise ContractError("E_CLOSURE_KIND")
        viewport, source, paths = raw["viewport"], raw.get("source"), raw.get("paths", ())
        if source is not None and not isinstance(source, FrozenDict):
            raise ContractError("E_CLOSURE_KIND")
        if not isinstance(paths, (FrozenList, tuple)) or not all(isinstance(path, FrozenDict) for path in paths):
            raise ContractError("E_CLOSURE_KIND")
        normalized: list[IconPath] = []
        for path in paths:
            data = path.get("data")
            if validate_geometry:
                _compact_commands(data)
            if not isinstance(data, str):
                raise ContractError("E_ICON_CATALOG_GEOMETRY")
            normalized.append(IconPath(str(path["paint"]), data,
                                       float(path["strokeWidth"]) if "strokeWidth" in path else None,
                                       str(path["lineCap"]) if "lineCap" in path else None,
                                       str(path["lineJoin"]) if "lineJoin" in path else None))
        raster = IconRasterSource(str(source["address"]), str(source["contentIdentity"])) if source is not None else None
        entries.append(IconEntry(str(name), str(raw["kind"]), (int(viewport["inlineSize"]), int(viewport["blockSize"])),
                                 str(raw["alternative"]), tuple(normalized), raster))
    aliases, provenance, entry_aliases = body["aliases"], body["provenance"], body["entryAliases"]
    if not isinstance(aliases, (FrozenList, tuple)) or not isinstance(provenance, FrozenDict) or not isinstance(entry_aliases, FrozenDict):
        raise ContractError("E_CLOSURE_KIND")
    return IconCatalogContract(identity, version, str(body["set"]), tuple(str(alias) for alias in aliases), provenance, entry_aliases, tuple(entries))


@cache
def _material_projection() -> FrozenDict:
    value = json.loads(files("chrona.resources").joinpath(_MATERIAL_PROJECTION).read_text(encoding="utf-8"))
    if not isinstance(value, Mapping):
        raise ContractError("E_ICON_CATALOG_SCHEMA")
    return freeze(value)


def packaged_icon_catalog_contract(reference: Mapping[str, Any], payload: bytes) -> IconCatalogContract | None:
    projection = _material_projection(); identity = "sha256:" + sha256(payload).hexdigest()
    if (reference.get("contentIdentity") != identity or projection.get("catalogIdentity") != identity
            or reference.get("id") != projection.get("id") or projection.get("version") != "chrona/icon-catalog/v0.3"):
        return None
    body = projection.get("body")
    if not isinstance(body, FrozenDict):
        raise ContractError("E_ICON_CATALOG_SCHEMA")
    raw_icons = body.get("icons")
    if not isinstance(raw_icons, FrozenDict):
        raise ContractError("E_ICON_CATALOG_SCHEMA")
    aliases, provenance, entry_aliases = body["aliases"], body["provenance"], body["entryAliases"]
    if not isinstance(aliases, (FrozenList, tuple)) or not isinstance(provenance, FrozenDict) or not isinstance(entry_aliases, FrozenDict):
        raise ContractError("E_ICON_CATALOG_SCHEMA")
    closure_identity = ClosureIdentity("icon-catalog", str(projection["id"]), str(reference["revision"]["token"]), identity)
    return IconCatalogContract(closure_identity, str(projection["version"]), str(body["set"]), tuple(str(item) for item in aliases),
                               provenance, entry_aliases, (), tuple(sorted(str(name) for name in raw_icons)), raw_icons)


def is_packaged_icon_projection(payload: bytes) -> bool:
    return _material_projection().get("catalogIdentity") == "sha256:" + sha256(payload).hexdigest()


@dataclass(frozen=True)
class PresentationPresetContract(ResourceContract):
    """Validated declarative preset package; resource documents stay external."""

    package_version: str
    resources: FrozenDict
    compatible_color_schemes: tuple[FrozenDict, ...]


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


_SCHEMAS = {
    ("render-context", "chrona/render-context/v0.12"): "render-context-v0.12.schema.yaml",
    ("project", "timeline/v0.6"): "project-v0.6.schema.yaml",
    ("view", "chrona/view/v0.12"): "view-v0.12.schema.yaml",
    ("theme", "chrona/theme/v0.5"): "theme-v0.5.schema.yaml",
    ("color-scheme", "chrona/color-scheme/v0.2"): "color-scheme-v0.2.schema.yaml",
    ("layout-profile", "chrona/layout-profile/v0.3"): "layout-profile-v0.3.schema.yaml",
    ("icon-catalog", "chrona/icon-catalog/v0.3"): "icon-catalog-v0.3.schema.yaml",
    ("actual-set", "chrona/actual-set/v0.2"): "actual-set-v0.2.schema.yaml",
    ("snapshot-ref", "chrona/snapshot-ref/v0.2"): "snapshot-ref-v0.2.schema.yaml",
    ("profile-package", "chrona/profile/v0.2"): "profile-v0.2.schema.yaml",
    ("summary-profile", "chrona/summary-profile/v0.1"): "summary-profile-v0.2.schema.yaml",
    ("review-detail-profile", "chrona/review-detail-profile/v0.1"): "review-detail-profile-v0.1.schema.yaml",
    ("presentation-preset", "chrona/presentation-preset/v0.1"): "presentation-preset-v0.1.schema.yaml",
    ("authoring-workspace", "chrona/authoring-workspace/v0.1"): "authoring-workspace-v0.1.schema.yaml",
}


@cache
def _registry() -> Registry:
    names = ("presentation-resource-v0.1.schema.yaml", "revision-store-resource-ref-v0.1.schema.yaml")
    registry = Registry()
    for name in names:
        schema = schema_document(name)
        registry = registry.with_resource(schema["$id"], Resource.from_contents(schema))
    return registry


def _validate(kind: str, value: Mapping[str, Any], identity: ClosureIdentity) -> str:
    version = value.get("version")
    schema_name = _SCHEMAS.get((kind, version)) if isinstance(version, str) else None
    if schema_name is None:
        raise ContractError("E_CLOSURE_KIND")
    schema = schema_document(schema_name)
    errors = tuple(jsonschema.Draft202012Validator(schema, registry=_registry()).iter_errors(_schema_value(value)))
    if errors:
        violation = explain_errors(errors, resource_kind=kind, resource_identity=identity.id)
        raise SchemaContractError(kind, violation.pointer, violation.message, violation)
    return version


def _schema_value(value: Any) -> Any:
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Mapping):
        return {key: _schema_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_schema_value(item) for item in value]
    return value


def _view_input(body: FrozenDict) -> ViewInput:
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
                             tuple(str(item) for item in raw_grouping.get("order", ())),
                             str(raw_grouping["missing"]) if "missing" in raw_grouping else None,
                             str(raw_grouping["presentation"]) if "presentation" in raw_grouping else None,
                             int(raw_grouping["depth"]) if "depth" in raw_grouping else None,
                             str(raw_grouping["rollup"]) if "rollup" in raw_grouping else None)
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
    return ViewInput(
        selection, grouping, ordering, window, comparison, visibility, body["layoutIntent"],
        tuple(TableColumn(str(column["id"]), column["source"], str(column.get("format", "text")),
                          str(column["missing"])) for column in body.get("tableColumns", ())),
        tuple(body.get("annotations", ())), ViewRows(str(rows["mode"]), row_items, str(rows.get("points", "own-row"))), body.get("axis"),
        tuple(body.get("markers", ())), body.get("shading"), body.get("timePresentation"),
        str(body["annotationPresentation"]) if "annotationPresentation" in body else None,
        str(body["surface"]), body.get("colorEncoding"),
        str(body["progressFill"]["source"]) if "progressFill" in body else None,
        tuple(ViewVisual(str(item["target"]["kind"]), item["target"], str(item["ref"]) if "ref" in item else None,
                         item.get("encoding"), str(item.get("side", "leading")), bool(item.get("decorative", True)))
              for item in body.get("visuals", ())) )


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
        raise ContractError("E_CLOSURE_KIND")
    version = _validate(identity.kind, value, identity)
    if identity.kind == "project":
        extensions = frozen.get("extensions", ())
        if not isinstance(extensions, (tuple, FrozenList)) or not all(isinstance(item, FrozenDict) for item in extensions):
            raise ContractError("E_CLOSURE_KIND")
        return ProjectContract(identity, version, frozen, tuple(extensions))
    if identity.kind == "view":
        return ViewContract(identity, version, _view_input(body))
    if identity.kind == "theme":
        return ThemeContract(identity, version, frozen)
    if identity.kind == "color-scheme":
        return ColorSchemeContract(identity, version, frozen)
    if identity.kind == "layout-profile":
        return LayoutProfileContract(identity, version, frozen)
    if identity.kind == "icon-catalog":
        return _icon_catalog_contract(identity, version, body, validate_geometry=True)
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
        raw_typesetter = environment.get("typesetter")
        if raw_typesetter is not None and not isinstance(raw_typesetter, FrozenDict):
            raise ContractError("E_CLOSURE_KIND")
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
        if not isinstance(package, FrozenDict) or not isinstance(resources, FrozenDict):
            raise ContractError("E_CLOSURE_KIND")
        if not isinstance(schemes, (FrozenList, tuple)) or not all(isinstance(item, FrozenDict) for item in schemes):
            raise ContractError("E_CLOSURE_KIND")
        return PresentationPresetContract(identity, version, str(package["version"]), resources, tuple(schemes))
    if identity.kind == "authoring-workspace":
        project, presentation = body["project"], body["presentation"]
        actuals = body.get("actuals", ())
        if not isinstance(project, FrozenDict) or not isinstance(presentation, FrozenDict):
            raise ContractError("E_CLOSURE_KIND")
        if not isinstance(actuals, (FrozenList, tuple)) or not all(isinstance(item, FrozenDict) for item in actuals):
            raise ContractError("E_CLOSURE_KIND")
        mode = str(presentation["mode"])
        binding = presentation.get("binding")
        resources = presentation.get("resources")
        receipt = presentation.get("receipt")
        if mode == "guided" and not isinstance(binding, FrozenDict):
            raise ContractError("E_CLOSURE_KIND")
        if mode == "explicit" and (not isinstance(resources, FrozenDict) or not isinstance(receipt, FrozenDict)):
            raise ContractError("E_CLOSURE_KIND")
        _validate_workspace_identifiers(project, actuals)
        return AuthoringWorkspaceContract(identity, version, project, tuple(actuals), mode,
                                         binding if isinstance(binding, FrozenDict) else None,
                                         resources if isinstance(resources, FrozenDict) else None,
                                         receipt if isinstance(receipt, FrozenDict) else None)
    raise ContractError("E_CLOSURE_KIND")


def _validate_workspace_identifiers(project: FrozenDict, actuals: FrozenList | tuple[Any, ...]) -> None:
    tasks = project.get("tasks", ())
    if not isinstance(tasks, (FrozenList, tuple)):
        raise ContractError("E_CLOSURE_KIND")
    task_ids = tuple(str(task["id"]) for task in tasks if isinstance(task, FrozenDict))
    if len(task_ids) != len(tasks) or len(task_ids) != len(set(task_ids)):
        raise ContractError("E_AUTHORING_TASK_ID")
    actual_ids = tuple(str(item["taskId"]) for item in actuals)
    if len(actual_ids) != len(set(actual_ids)) or any(task_id not in task_ids for task_id in actual_ids):
        raise ContractError("E_AUTHORING_ACTUAL_TASK")
