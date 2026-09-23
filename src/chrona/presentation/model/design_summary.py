"""Read-only Design Space inspection over an already resolved render closure."""
from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Mapping

from chrona.presentation.model.closure import RenderClosure


class DesignSummaryError(ValueError):
    """A closure cannot support a finite, identity-bearing design summary."""


@dataclass(frozen=True)
class SummarySource:
    """Identity of the ordinary resource that owns an inspected value."""

    id: str
    kind: str
    content_identity: str

    def as_data(self) -> dict[str, str]:
        return {"id": self.id, "kind": self.kind, "contentIdentity": self.content_identity}


@dataclass(frozen=True)
class SummaryValue:
    """One finite authored intent with its owning ordinary resource."""

    value: Any
    source: SummarySource

    def as_data(self) -> dict[str, Any]:
        return {"value": _plain(self.value), "source": self.source.as_data()}


@dataclass(frozen=True)
class PresentationDesignSummary:
    """Immutable inspection output; it is never accepted as render input."""

    origin: str
    provenance: Mapping[str, SummarySource]
    dimensions: Mapping[str, Mapping[str, SummaryValue]]

    def as_data(self) -> dict[str, Any]:
        return {
            "format": "chrona/presentation-design-summary/v0.1",
            "provenance": {"origin": self.origin, **{key: value.as_data() for key, value in self.provenance.items()}},
            "dimensions": {
                dimension: {key: value.as_data() for key, value in values.items()}
                for dimension, values in self.dimensions.items()
            },
        }


def summarize_presentation(closure: RenderClosure, *, origin: str | None = None) -> PresentationDesignSummary:
    """Project finite authored Design Space intent from a completed closure.

    This function only reads contracts already present in ``closure``.  It does
    not normalize, locate files, resolve a package, schedule, lay out, or
    render.  Values without a stable finite interpretation are deliberately
    absent rather than inferred.
    """
    resources = {item.kind: item for item in closure.resources}
    required = ("view", "layout-profile", "theme", "color-scheme")
    if any(kind not in resources for kind in required):
        raise DesignSummaryError("E_DESIGN_SUMMARY_INPUT")
    sources = {
        "view": _source(resources["view"]), "layout": _source(resources["layout-profile"]),
        "theme": _source(resources["theme"]), "colorScheme": _source(resources["color-scheme"]),
    }
    if any(not value.content_identity.startswith("sha256:") for value in sources.values()):
        raise DesignSummaryError("E_DESIGN_SUMMARY_IDENTITY")
    actual_origin = origin or ("guided" if closure.guided_provenance else "explicit")
    if actual_origin not in {"explicit", "guided", "materialized"}:
        raise DesignSummaryError("E_DESIGN_SUMMARY_INPUT")
    view = closure.view.view
    layout = resources["layout-profile"].contract.layout_input
    theme = resources["theme"].contract.theme_input
    scheme = resources["color-scheme"].contract.scheme_input
    dimensions = {
        "content": _values(sources["view"], {
            "surface": view.surface, "selection": _selection(view), "grouping": _grouping(view),
            "ordering": _ordering(view), "window": _window(view), "comparison": _comparison(view),
            "visibility": _visibility(view), "tableColumns": tuple(column.id for column in view.table_columns),
            "annotationPresentation": view.annotation_presentation,
        }),
        "composition": _values(sources["layout"], {
            "writingMode": layout.get("writingMode"), "rootKind": _mapping_value(layout.get("root"), "kind"),
            "slots": tuple(_slots(layout.get("root"))), "overflow": tuple(_overflow(layout.get("root"))),
        }),
        "visualGrammar": _values(sources["view"], {
            "rowsMode": view.rows.mode, "itemTracks": tuple(sorted({item.track for row in view.rows.items for item in row.items})),
            "relations": view.visibility.relations, "markers": tuple(str(item.get("kind", item.get("id", "marker"))) for item in view.markers),
        }),
        "appearance": _values(sources["theme"], {
            "themeRoles": tuple(sorted(theme.get("body", {}).get("roles", {}).keys())),
            "themeTokens": tuple(sorted(theme.get("body", {}).get("values", {}).keys())),
        }) | _values(sources["colorScheme"], {
            "schemeRoles": tuple(sorted(scheme.get("body", {}).get("colors", {}).keys())),
            "suitability": scheme.get("body", {}).get("suitability"),
        }),
    }
    return PresentationDesignSummary(actual_origin, MappingProxyType(sources), MappingProxyType({
        name: MappingProxyType(values) for name, values in dimensions.items()
    }))


def _source(resource: Any) -> SummarySource:
    return SummarySource(resource.id, resource.kind, resource.content_identity)


def _values(source: SummarySource, values: Mapping[str, Any]) -> dict[str, SummaryValue]:
    return {key: SummaryValue(_freeze_value(value), source) for key, value in values.items() if value is not None and value != ()}


def _plain(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _plain(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_plain(item) for item in value]
    return value


def _freeze_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return MappingProxyType({str(key): _freeze_value(item) for key, item in value.items()})
    if isinstance(value, (tuple, list)):
        return tuple(_freeze_value(item) for item in value)
    return value


def _mapping_value(value: Any, key: str) -> Any:
    return value.get(key) if isinstance(value, Mapping) else None


def _slots(node: Any) -> list[str]:
    if not isinstance(node, Mapping):
        return []
    own = [str(node["source"])] if node.get("kind") == "slot" and isinstance(node.get("source"), str) else []
    return own + [item for child in node.get("children", ()) for item in _slots(child)]


def _overflow(node: Any) -> list[str]:
    if not isinstance(node, Mapping):
        return []
    own = [str(node["overflow"])] if isinstance(node.get("overflow"), str) else []
    return own + [item for child in node.get("children", ()) for item in _overflow(child)]


def _selection(value: Any) -> Mapping[str, Any] | None:
    return None if value.selection is None else {"ids": value.selection.ids, "types": value.selection.types,
                                                   "objectTypes": value.selection.object_types,
                                                   "excludedObjectTypes": value.selection.excluded_object_types}


def _grouping(value: Any) -> Mapping[str, Any] | None:
    return None if value.grouping is None else {"by": value.grouping.by, "field": value.grouping.field,
                                                 "presentation": value.grouping.presentation, "depth": value.grouping.depth}


def _ordering(value: Any) -> Mapping[str, Any] | None:
    return None if value.ordering is None else {"by": value.ordering.by, "direction": value.ordering.direction,
                                                 "tieBreak": value.ordering.tie_break}


def _window(value: Any) -> Mapping[str, Any]:
    return {"mode": value.window.mode, "marginDays": value.window.margin_days}


def _comparison(value: Any) -> Mapping[str, Any]:
    return {"baseline": value.comparison.baseline, "actual": value.comparison.actual,
            "facets": value.comparison.facets, "deltaUnit": value.comparison.delta_unit}


def _visibility(value: Any) -> Mapping[str, Any]:
    return {"labels": _plain(value.visibility.labels), "relations": _plain(value.visibility.relations),
            "annotations": _plain(value.visibility.annotations)}
