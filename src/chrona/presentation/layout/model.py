"""Immutable values shared by the intent-oriented layout resolver and engine."""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
import json
from typing import Any, Mapping


class LayoutError(ValueError):
    """Stable M24 layout diagnostic."""

    def __init__(self, diagnostic_id: str, path: str = "", node_id: str | None = None, detail: str = ""):
        super().__init__(diagnostic_id + (f": {detail}" if detail else ""))
        self.diagnostic_id = diagnostic_id
        self.path = path
        self.node_id = node_id
        self.detail = detail


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
    writing_mode: str
    viewport: Rect
    decisions: tuple[LayoutDecision, ...]
    diagnostics: tuple[str, ...] = ()
    relation_max_bends: int = 4
    relation_max_detour_ratio: float = 2.0
    row_distribution: str = "pack"

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
            "reviewSurface": {"rowDistribution": self.row_distribution},
            "viewport": rect(self.viewport),
            "writingMode": self.writing_mode,
        }
        return json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode()
