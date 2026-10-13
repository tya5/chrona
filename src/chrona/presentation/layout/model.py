"""Immutable values shared by the intent-oriented layout resolver and engine."""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
from math import fsum, inf, nextafter
from collections.abc import Iterable
import json
from typing import Any, Mapping, TYPE_CHECKING

from chrona.presentation.layout.numbers import LayoutNumber, NumericConversionError, from_source_float

if TYPE_CHECKING:
    from chrona.presentation.layout.surface_quality import FitWarning


class RelationUnroutableMode(str, Enum):
    """Declared Layout resolution, independent of View admission/network policy."""

    RELAX = "relax"
    OVERLAP = "overlap"
    STUB = "stub"
    SUPPRESS = "suppress"


class LayoutError(ValueError):
    """Stable M24 layout diagnostic."""

    def __init__(self, diagnostic_id: str, path: str = "", node_id: str | None = None, detail: str = ""):
        super().__init__(diagnostic_id + (f": {detail}" if detail else ""))
        self.diagnostic_id = diagnostic_id
        self.path = path
        self.node_id = node_id
        self.detail = detail


class CountDependentHeadingFitError(LayoutError):
    """An owner-detected intrinsic text fit failure with closed figure dependencies."""

    def __init__(self, path: str, source_id: str | None, detail: str, figure_ids: frozenset[str]):
        if not figure_ids:
            raise ValueError("dependent text fit requires declared figure dependencies")
        super().__init__("E_LAYOUT_TEXT_OVERFLOW", path, source_id, detail)
        self.figure_ids = figure_ids


def native_number(value: Any, *, path: str = "/layout/number", node_id: str | None = None) -> LayoutNumber:
    """Admit one resolved numeric fact without changing resource arithmetic."""
    try:
        return from_source_float(value) if isinstance(value, float) else LayoutNumber(value)
    except (TypeError, ValueError) as error:
        raise LayoutError("E_LAYOUT_NUMERIC_CONVERSION", path, node_id,
                          f"stage=native-input; {error}") from error


def projected_number(value: Any, *, path: str = "/layout/number", node_id: str | None = None,
                     stage: str = "output") -> float:
    """Project completed geometry, retaining the owning diagnostic boundary."""
    number = native_number(value, path=path, node_id=node_id)
    try:
        return number.to_float()
    except NumericConversionError as error:
        raise LayoutError("E_LAYOUT_NUMERIC_CONVERSION", path, node_id,
                          f"stage={stage}; {error}") from error


def source_budget_float(value: Any, *, path: str, node_id: str | None = None) -> float:
    """Use the largest adjacent library value that does not enlarge a native ceiling."""
    budget = native_number(value, path=path, node_id=node_id)
    result = projected_number(budget, path=path, node_id=node_id, stage="font-interface")
    if from_source_float(result) > budget:
        result = nextafter(result, -inf)
    if not result > -inf or from_source_float(result) > budget:
        raise LayoutError("E_LAYOUT_NUMERIC_CONVERSION", path, node_id,
                          "stage=font-interface; converted width exceeds native ceiling")
    return result


def geometry_sum(values: Iterable[float]) -> float:
    """Correctly round one Layout-owned float geometry accumulation.

    Decimal profile arithmetic intentionally remains outside this helper.  A
    completed placement must never inherit the Python-minor-dependent builtin
    float ``sum`` algorithm.
    """
    result = tuple(values)
    if any(isinstance(value, bool) or not isinstance(value, (int, float)) for value in result):
        index = next(position for position, value in enumerate(result)
                     if isinstance(value, bool) or not isinstance(value, (int, float)))
        raise TypeError(f"E_LAYOUT_GEOMETRY_SUM_INPUT: item_index={index}, "
                        f"actual_type={type(result[index]).__name__}, expected=int-or-float")
    return fsum(result)


@dataclass(frozen=True)
class Rect:
    inline: LayoutNumber
    block: LayoutNumber
    inline_size: LayoutNumber
    block_size: LayoutNumber

    def __post_init__(self) -> None:
        for name in ("inline", "block", "inline_size", "block_size"):
            object.__setattr__(self, name, native_number(getattr(self, name), path=f"/geometry/{name}"))


@dataclass(frozen=True)
class Measurement:
    min_inline: LayoutNumber
    preferred_inline: LayoutNumber
    max_inline: LayoutNumber
    min_block: LayoutNumber
    preferred_block: LayoutNumber
    max_block: LayoutNumber
    first_baseline: LayoutNumber | None = None
    last_baseline: LayoutNumber | None = None
    figure_dependencies: frozenset[str] = frozenset()

    def __post_init__(self) -> None:
        for name in ("min_inline", "preferred_inline", "max_inline", "min_block", "preferred_block", "max_block",
                     "first_baseline", "last_baseline"):
            value = getattr(self, name)
            if value is not None:
                object.__setattr__(self, name, native_number(value, path=f"/measurement/{name}"))


@dataclass(frozen=True)
class ResolvedLayoutProfile:
    profile_id: str
    content_hash: str
    profile: Mapping[str, Any]
    distances: Mapping[str, Decimal]
    literal_distance_paths: tuple[str, ...]


@dataclass(frozen=True)
class RegionFrame:
    """A node's region-frame declaration with what the engine knows when it has arranged the subtree (#889).

    ``inset`` is the declared Layout distance (zero when absent). ``populated`` is true for a slot and for a
    container with at least one slot of positive area beneath it: a panel with nothing in it is not drawn.
    """

    inset: Decimal
    populated: bool
    paint: str | None = None


SLOT_HEADING_ALIGNS = ("start", "center", "end")
SLOT_HEADING_BLOCKS = ("top", "header-row", "axis-tier", "start-column")


@dataclass(frozen=True)
class SlotHeading:
    """A slot's declared caption (#1064): copy and placement intent; Layout completes the text and the reserve."""

    text: str | None
    align: str = "start"
    block: str = "top"
    gap: Decimal | None = None  # a `start-column` caption's declared gap to the entries (#1392); None keeps half the font size
    template: str | None = None


@dataclass(frozen=True)
class LayoutDecision:
    node_id: str
    kind: str
    bounds: Rect
    source: str | None = None
    alignment: Mapping[str, str] = field(default_factory=dict)
    references: tuple[str, ...] = ()
    priority: str | None = None
    overflow: str | None = None
    direction: str | None = None
    gap: Decimal | None = None
    item_min_inline_size: Decimal | None = None
    frame: RegionFrame | None = None
    heading: SlotHeading | None = None
    columns: int | None = None
    column_distribution: str = "start"


@dataclass(frozen=True)
class LayoutManifest:
    profile_id: str
    profile_hash: str
    flow_direction: str
    dependency_network_flow_direction: str
    viewport: Rect
    decisions: tuple[LayoutDecision, ...]
    diagnostics: tuple[str, ...] = ()
    relation_max_bends: int = 4
    relation_max_detour_ratio: float = 2.0
    relation_entry: str = "side-when-free"
    annotation_max_bends: int = 4
    annotation_max_detour_ratio: float = 2.0
    row_distribution: str = "pack"
    background_extents: Mapping[str, str] = field(default_factory=dict)
    member_names: Mapping[str, Any] = field(default_factory=dict)
    fit_warnings: tuple[FitWarning, ...] = ()
    relation_search: str = "first-fit"
    relation_search_budget: int | None = None
    # Staged implementation: flip only after recovery and target protection land.
    relation_unroutable: RelationUnroutableMode = RelationUnroutableMode.RELAX

    def canonical_bytes(self, precision: int = 3) -> bytes:
        def number(value: LayoutNumber | Decimal) -> str:
            try:
                return native_number(value).format_decimal(precision)
            except NumericConversionError as error:
                raise LayoutError("E_LAYOUT_NUMERIC_CONVERSION", "/layoutManifest",
                                  detail=f"stage=manifest; {error}") from error

        def rect(value: Rect) -> dict[str, str]:
            return {
                "block": number(value.block),
                "blockSize": number(value.block_size),
                "inline": number(value.inline),
                "inlineSize": number(value.inline_size),
            }

        def node(item: LayoutDecision) -> dict[str, Any]:
            value = {
                "alignment": dict(sorted(item.alignment.items())),
                "bounds": rect(item.bounds),
                "id": item.node_id,
                "kind": item.kind,
                "references": list(item.references),
                "priority": item.priority,
                "overflow": item.overflow,
                "source": item.source,
            }
            if item.frame is not None:
                frame = {"inset": number(item.frame.inset), "populated": item.frame.populated}
                if item.frame.paint is not None:
                    frame["paint"] = item.frame.paint
                value["frame"] = frame
            if item.heading is not None:
                copy = {"text": item.heading.text} if item.heading.text is not None else {"template": item.heading.template}
                value["heading"] = {"align": item.heading.align, "block": item.heading.block, **copy}
            return value

        payload = {
            "diagnostics": list(self.diagnostics),
            "nodes": [node(item) for item in sorted(self.decisions, key=lambda value: value.node_id)],
            "profileHash": self.profile_hash,
            "profileId": self.profile_id,
            "relationRouting": {
                "maxBends": self.relation_max_bends,
                "maxDetourRatio": self.relation_max_detour_ratio,
                **({"entry": self.relation_entry} if self.relation_entry != "side-when-free" else {}),
                **({"search": self.relation_search} if self.relation_search != "best" else {}),
                **({"searchBudget": self.relation_search_budget} if self.relation_search_budget is not None else {}),
                **({"unroutable": self.relation_unroutable.value}
                   if self.relation_unroutable != RelationUnroutableMode.SUPPRESS else {}),
            },
            "annotationRouting": {
                "maxBends": self.annotation_max_bends,
                "maxDetourRatio": self.annotation_max_detour_ratio,
            },
            "reviewSurface": {
                "backgroundExtents": dict(sorted(self.background_extents.items())),
                "rowDistribution": self.row_distribution,
            },
            "viewport": rect(self.viewport),
            "flowDirection": self.flow_direction,
            "dependencyNetworkFlowDirection": self.dependency_network_flow_direction,
        }
        if self.member_names:
            payload["reviewSurface"]["memberNames"] = dict(sorted(self.member_names.items()))
        if self.fit_warnings:
            payload["fitWarnings"] = [
                {"code": item.code, "placementId": item.placement_id,
                 "requiredInline": item.required_inline, "requiredBlock": item.required_block,
                 "availableInline": item.available_inline, "availableBlock": item.available_block}
                for item in self.fit_warnings
            ]
        return json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode()
