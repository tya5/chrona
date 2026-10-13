"""Pure closure for View-owned Summary Profile connections and wording."""
from __future__ import annotations

from dataclasses import dataclass, replace
from collections.abc import Mapping

from chrona.presentation.contracts.resources import (
    ReviewDetailInput, SummaryMetric, SummaryPanelInput,
    SummaryProfileInput, ViewInput, freeze,
)


class ProfileConnectionError(ValueError):
    """A cross-resource profile binding or wording failure with its View pointer."""

    def __init__(self, code: str, detail: str, source_ref: str, *, component: str = "view") -> None:
        super().__init__(code)
        self.code = code
        self.detail = detail
        self.source_ref = source_ref
        self.component = component


@dataclass(frozen=True)
class ProfileOmission:
    """A profile metric omitted without changing authored panel/metric indexes."""

    panel_index: int
    metric_index: int
    panel_id: str
    metric_id: str
    source_kind: str
    source_name: str
    source_ref: str

    @property
    def code(self) -> str:
        return "I_SUMMARY_SLOT_UNBOUND" if self.source_kind == "slot" else "I_SUMMARY_FIGURE_UNBOUND"


@dataclass(frozen=True)
class ProfileConnectionResult:
    """Effective typed inputs plus original-index omission facts for render wiring."""

    view: ViewInput
    summary: SummaryProfileInput | None
    detail: ReviewDetailInput | None
    omissions: tuple[ProfileOmission, ...]


def _pointer_token(value: str) -> str:
    return value.replace("~", "~0").replace("/", "~1")


def _source_slot(source: object) -> str | None:
    return source.get("slot") if isinstance(source, Mapping) and isinstance(source.get("slot"), str) else None


def _metric_id(metric: SummaryMetric | tuple[str, str]) -> str:
    return metric.id if isinstance(metric, SummaryMetric) else metric[0]


def resolve_profile_connections(view: ViewInput, summary: SummaryProfileInput | None,
                                detail: ReviewDetailInput | None, *,
                                project_object_ids: frozenset[str]) -> ProfileConnectionResult:
    """Close slot names and View wording without filtering or mutating profile entries.

    The View parser has already typed figure bindings and placed their FigureSpecs
    in ``view.figures``. This boundary resolves only cross-resource names and
    profile-facing wording; Core remains the owner of figure fact resolution.
    """
    bindings = {binding.name: binding for binding in view.profile_bindings}
    declared_slots = {
        slot
        for panel in (summary.panels if summary is not None else ())
        for metric in panel.metrics
        if isinstance(metric, SummaryMetric)
        if (slot := _source_slot(metric.source)) is not None
    }

    for binding in view.profile_bindings:
        if binding.name not in declared_slots:
            raise ProfileConnectionError("E_VIEW_BINDING_UNKNOWN",
                                         f"binding slot {binding.name!r} is not declared by the selected Summary Profile",
                                         binding.path)
        if binding.object_id is not None and binding.object_id not in project_object_ids:
            raise ProfileConnectionError("E_FIGURE_OBJECT_UNKNOWN",
                                         f"binding names no Project object {binding.object_id!r}",
                                         f"{binding.path}/object")

    omissions: list[ProfileOmission] = []
    effective_panels: list[SummaryPanelInput] = []
    declared_figures = {figure.figure_id for figure in view.figures}
    for panel_index, panel in enumerate(summary.panels if summary is not None else ()):
        effective_metrics: list[SummaryMetric | tuple[str, str]] = []
        for metric_index, metric in enumerate(panel.metrics):
            if not isinstance(metric, SummaryMetric):
                effective_metrics.append(metric)
                continue
            source = metric.source
            declaration_path = metric.declaration_path or f"/body/panels/{panel_index}/metrics/{metric_index}"
            source_path = f"{declaration_path}/source"
            slot = _source_slot(source)
            if slot is not None:
                binding = bindings.get(slot)
                if binding is None:
                    omissions.append(ProfileOmission(panel_index, metric_index, panel.id, metric.id,
                                                     "slot", slot,
                                                     source_path))
                    effective_metrics.append(metric)
                    continue
                if metric.scope == "subtree" and binding.object_id is None:
                    raise ProfileConnectionError("E_PRESENTATION_SUMMARY_SOURCE",
                                                 "subtree scope requires a planned-object slot binding",
                                                 source_path,
                                                 component="presentation")
                source = freeze({"object": binding.object_id, "facet": "planned"}
                                if binding.object_id is not None else {"figure": slot})
                metric = replace(metric, source=source)
            elif isinstance(source, Mapping) and isinstance(source.get("figure"), str):
                figure_id = source["figure"]
                if figure_id not in declared_figures:
                    omissions.append(ProfileOmission(panel_index, metric_index, panel.id, metric.id,
                                                     "figure", figure_id,
                                                     source_path))
                    effective_metrics.append(metric)
                    continue
            effective_metrics.append(metric)
        effective_panels.append(replace(panel, metrics=tuple(effective_metrics)))

    effective_summary = (replace(summary, panels=tuple(effective_panels))
                         if summary is not None else None)
    effective_detail = detail
    wording = view.wording or {}

    summary_wording = wording.get("summary", {})
    if summary_wording:
        matches: dict[str, list[tuple[int, int]]] = {}
        for panel_index, panel in enumerate(effective_summary.panels if effective_summary else ()):
            for metric_index, metric in enumerate(panel.metrics):
                key = f"{panel.id}.{_metric_id(metric)}"
                matches.setdefault(key, []).append((panel_index, metric_index))
        overrides: dict[tuple[int, int], str] = {}
        for key, text in summary_wording.items():
            pointer = f"/body/wording/summary/{_pointer_token(str(key))}"
            found = matches.get(str(key), ())
            if not found:
                raise ProfileConnectionError("E_VIEW_WORDING_UNKNOWN", f"summary wording key {key!r} names no profile metric", pointer)
            if len(found) != 1:
                raise ProfileConnectionError("E_VIEW_WORDING_AMBIGUOUS", f"summary wording key {key!r} matches more than one profile metric", pointer)
            overrides[found[0]] = str(text)
        if effective_summary is not None:
            panels = []
            for panel_index, panel in enumerate(effective_summary.panels):
                metrics = tuple(
                    replace(metric, label=overrides[(panel_index, metric_index)])
                    if (panel_index, metric_index) in overrides and isinstance(metric, SummaryMetric)
                    else metric
                    for metric_index, metric in enumerate(panel.metrics)
                )
                panels.append(replace(panel, metrics=metrics))
            effective_summary = replace(effective_summary, panels=tuple(panels))

    legend_wording = wording.get("legend", {})
    if legend_wording:
        declared_roles = {entry.role for entry in (detail.legend if detail is not None else ())}
        for role in legend_wording:
            if role not in declared_roles:
                pointer = f"/body/wording/legend/{_pointer_token(str(role))}"
                raise ProfileConnectionError("E_VIEW_WORDING_UNKNOWN", f"legend wording role {role!r} is not declared by the selected Detail Profile", pointer)
        if detail is not None:
            effective_detail = replace(
                detail,
                legend=tuple(replace(entry, label=str(legend_wording[entry.role]))
                             if entry.role in legend_wording else entry
                             for entry in detail.legend),
            )

    return ProfileConnectionResult(view, effective_summary, effective_detail, tuple(omissions))
