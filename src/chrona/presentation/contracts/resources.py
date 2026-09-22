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


@dataclass(frozen=True)
class ViewSelection:
    ids: tuple[str, ...]
    types: tuple[str, ...]


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
    environment: RenderEnvironment
    target: RenderTarget


@dataclass(frozen=True)
class ResolvedThemeContract:
    """The frozen derived decorative value permitted past closure resolution."""

    source_theme_id: str
    resolved_input: FrozenDict


_SCHEMAS = {
    ("render-context", "chrona/render-context/v0.8"): "render-context-v0.8.schema.yaml",
    ("project", "timeline/v0.5"): "project-v0.5.schema.yaml",
    ("view", "chrona/view/v0.7"): "view-v0.7.schema.yaml",
    ("theme", "chrona/theme/v0.2"): "theme-v0.2.schema.yaml",
    ("color-scheme", "chrona/color-scheme/v0.1"): "color-scheme-v0.1.schema.yaml",
    ("layout-profile", "chrona/layout-profile/v0.2"): "layout-profile-v0.2.schema.yaml",
    ("actual-set", "chrona/actual-set/v0.2"): "actual-set-v0.2.schema.yaml",
    ("snapshot-ref", "chrona/snapshot-ref/v0.2"): "snapshot-ref-v0.2.schema.yaml",
    ("profile-package", "chrona/profile/v0.2"): "profile-v0.2.schema.yaml",
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


def _view_input(body: FrozenDict) -> ViewInput:
    rows = body["rows"]
    raw_selection = body.get("selection", FrozenDict())
    raw_include = raw_selection.get("include", FrozenDict())
    selection = ViewSelection(tuple(str(item) for item in raw_include.get("ids", ())),
                              tuple(str(item) for item in raw_include.get("types", ()))) if raw_selection else None
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
        tuple(body.get("annotations", ())), ViewRows(str(rows["mode"]), row_items), body.get("axis"),
        tuple(body.get("markers", ())), body.get("shading"), body.get("timePresentation"),
        str(body["annotationPresentation"]) if "annotationPresentation" in body else None)


def _validate_view_fallback(raw_fallback: Any) -> None:
    """Reject non-operational preference ladders at the typed View boundary."""
    if not isinstance(raw_fallback, Mapping):
        return
    allowed = {
        "labels": {"above", "below", "start", "end", "suppress"},
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
    version = _validate(identity.kind, value)
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
            RenderEnvironment(int(viewport["inlineSize"]), int(viewport["blockSize"]), str(environment["locale"]),
                              environment["fontMetrics"], int(environment["scenePrecision"]), rasterizer, typesetter),
            RenderTarget(str(target["kind"]), tuple(str(item) for item in target["capabilities"]),
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
    raise ContractError("E_CLOSURE_KIND")
