"""Immutable values shared by the intent-oriented layout resolver and engine."""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from math import fsum
from collections.abc import Iterable
import json
from typing import Any, Mapping, TYPE_CHECKING

if TYPE_CHECKING:
    from chrona.presentation.layout.surface_quality import FitWarning


class LayoutError(ValueError):
    """Stable M24 layout diagnostic."""

    def __init__(self, diagnostic_id: str, path: str = "", node_id: str | None = None, detail: str = ""):
        super().__init__(diagnostic_id + (f": {detail}" if detail else ""))
        self.diagnostic_id = diagnostic_id
        self.path = path
        self.node_id = node_id
        self.detail = detail


def geometry_sum(values: Iterable[float]) -> float:
    """Correctly round one Layout-owned float geometry accumulation.

    Decimal profile arithmetic intentionally remains outside this helper.  A
    completed placement must never inherit the Python-minor-dependent builtin
    float ``sum`` algorithm.
    """
    result = tuple(values)
    if any(isinstance(value, bool) or not isinstance(value, (int, float)) for value in result):
        raise TypeError("E_LAYOUT_GEOMETRY_SUM_INPUT")
    return fsum(result)


@dataclass(frozen=True)
class Rect:
    inline: Decimal
    block: Decimal
    inline_size: Decimal
    block_size: Decimal


@dataclass(frozen=True)
class Measurement:
    min_inline: Decimal
    preferred_inline: Decimal
    max_inline: Decimal
    min_block: Decimal
    preferred_block: Decimal
    max_block: Decimal
    first_baseline: Decimal | None = None
    last_baseline: Decimal | None = None


@dataclass(frozen=True)
class ResolvedLayoutProfile:
    profile_id: str
    content_hash: str
    profile: Mapping[str, Any]
    distances: Mapping[str, Decimal]
    literal_distance_paths: tuple[str, ...]


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
    annotation_max_bends: int = 4
    annotation_max_detour_ratio: float = 2.0
    row_distribution: str = "pack"
    background_extents: Mapping[str, str] = field(default_factory=dict)
    fit_warnings: tuple[FitWarning, ...] = ()

    def canonical_bytes(self, precision: int = 3) -> bytes:
        quantum = Decimal(1).scaleb(-precision)

        def number(value: Decimal) -> str:
            return format(value.quantize(quantum), "f")

        def rect(value: Rect) -> dict[str, str]:
            return {
                "block": number(value.block),
                "blockSize": number(value.block_size),
                "inline": number(value.inline),
                "inlineSize": number(value.inline_size),
            }

        payload = {
            "diagnostics": list(self.diagnostics),
            "nodes": [
                {
                    "alignment": dict(sorted(item.alignment.items())),
                    "bounds": rect(item.bounds),
                    "id": item.node_id,
                    "kind": item.kind,
                    "references": list(item.references),
                    "priority": item.priority,
                    "overflow": item.overflow,
                    "source": item.source,
                }
                for item in sorted(self.decisions, key=lambda value: value.node_id)
            ],
            "profileHash": self.profile_hash,
            "profileId": self.profile_id,
            "relationRouting": {
                "maxBends": self.relation_max_bends,
                "maxDetourRatio": self.relation_max_detour_ratio,
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
        if self.fit_warnings:
            payload["fitWarnings"] = [
                {"code": item.code, "placementId": item.placement_id,
                 "requiredInline": item.required_inline, "requiredBlock": item.required_block,
                 "availableInline": item.available_inline, "availableBlock": item.available_block}
                for item in self.fit_warnings
            ]
        return json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode()
