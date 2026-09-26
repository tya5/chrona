"""Renderer-neutral, typed annotation placement intent."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PlacementRegion:
    kind: str
    source: str | None = None


@dataclass(frozen=True)
class PlacementSearch:
    kind: str
    side: str | None = None
    max_positions: int = 1
    max_inline_em: float | None = None


@dataclass(frozen=True)
class PlacementObstacles:
    classes: tuple[str, ...]


@dataclass(frozen=True)
class PlacementConnector:
    kind: str


@dataclass(frozen=True)
class PlacementCandidate:
    candidate_id: str
    region: PlacementRegion
    search: PlacementSearch
    obstacles: PlacementObstacles
    connector: PlacementConnector


SHARED_OBSTACLES = PlacementObstacles((
    "mark", "text", "label-visual", "dependency-route", "leader-route",
    "annotation-box", "port", "rule",
))


def legacy_candidate(rung: str, purpose: str) -> PlacementCandidate:
    """Expand one published View rung without choosing any geometry."""
    connector = PlacementConnector("none" if purpose == "highlight" else "leader")
    if rung == "rail":
        return PlacementCandidate(rung, PlacementRegion("slot", "annotations"),
                                  PlacementSearch("row-aligned"), SHARED_OBSTACLES, connector)
    if rung in {"above", "below", "start", "end"}:
        return PlacementCandidate(rung, PlacementRegion("side", "annotations"),
                                  PlacementSearch("adjacent", side=rung), SHARED_OBSTACLES, connector)
    raise ValueError("E_PRESENTATION_CANDIDATE_INVALID")


def legacy_candidate_order(purpose: str, fallback_ladder: tuple[str, ...],
                           preferred: str | None = None
                           ) -> tuple[tuple[PlacementCandidate, ...], tuple[str, ...]]:
    """Keep the old preferred-rung insertion and suppress terminal outcome."""
    default_ladder = fallback_ladder or ("rail",)
    ladder = ((preferred,) + tuple(rung for rung in default_ladder if rung != preferred)
              if preferred else default_ladder)
    candidates = tuple(legacy_candidate(rung, purpose) for rung in ladder if rung != "suppress")
    return candidates, ladder


def candidate_order(candidates: tuple[PlacementCandidate, ...], purpose: str,
                    fallback_ladder: tuple[str, ...], preferred: str | None = None
                    ) -> tuple[tuple[PlacementCandidate, ...], tuple[str, ...]]:
    """Consume normalized data, inserting only a declared legacy preference."""
    if not candidates:
        return legacy_candidate_order(purpose, fallback_ladder, preferred)
    if not fallback_ladder:
        return candidates, tuple(candidate.candidate_id for candidate in candidates)
    ladder = ((preferred,) + tuple(rung for rung in fallback_ladder if rung != preferred)
              if preferred else fallback_ladder)
    by_id = {candidate.candidate_id: candidate for candidate in candidates}
    if preferred is not None and preferred not in by_id:
        by_id[preferred] = legacy_candidate(preferred, purpose)
    return tuple(by_id[rung] for rung in ladder if rung != "suppress"), ladder
