"""Renderer-neutral, typed annotation placement intent."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


@dataclass(frozen=True)
class PlacementRegion:
    kind: str
    source: str | None = None
    members: tuple["PlacementRegion", ...] = ()


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

REGION_KINDS = frozenset({"plot", "content", "slot", "intersection"})
SEARCH_KINDS = frozenset({"row-aligned", "adjacent", "nearest-free"})
CONNECTOR_KINDS = frozenset({"none", "leader", "tail"})
# Plot/content search cannot omit any shared obstacle class (#466 design).
_MANDATORY_PLOT_CLASSES = frozenset(SHARED_OBSTACLES.classes)


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


def _parse_region(raw: Mapping[str, Any]) -> PlacementRegion:
    kind = raw.get("kind")
    if kind not in REGION_KINDS:
        raise ValueError("E_PRESENTATION_CANDIDATE_INVALID")
    if kind == "intersection":
        members_raw = raw.get("of")
        if not isinstance(members_raw, (list, tuple)) or len(members_raw) != 2:
            raise ValueError("E_PRESENTATION_CANDIDATE_INVALID")
        return PlacementRegion(kind, members=tuple(_parse_region(member) for member in members_raw))
    source = raw.get("source")
    if kind == "slot" and not isinstance(source, str):
        raise ValueError("E_PRESENTATION_CANDIDATE_INVALID")
    return PlacementRegion(kind, source=str(source) if isinstance(source, str) else None)


def _parse_search(raw: Mapping[str, Any]) -> PlacementSearch:
    kind = raw.get("kind")
    if kind not in SEARCH_KINDS:
        raise ValueError("E_PRESENTATION_CANDIDATE_INVALID")
    side = raw.get("side")
    if kind == "adjacent" and side not in {"above", "below", "start", "end"}:
        raise ValueError("E_PRESENTATION_CANDIDATE_INVALID")
    max_positions = raw.get("maxPositions", 1)
    if not isinstance(max_positions, int) or isinstance(max_positions, bool) or not 1 <= max_positions <= 1024:
        raise ValueError("E_PRESENTATION_CANDIDATE_INVALID")
    max_inline_em = raw.get("maxInlineEm")
    if kind == "nearest-free":
        if max_inline_em is not None and not (isinstance(max_inline_em, (int, float))
                                               and not isinstance(max_inline_em, bool) and max_inline_em > 0):
            raise ValueError("E_PRESENTATION_CANDIDATE_INVALID")
    elif max_inline_em is not None:
        raise ValueError("E_PRESENTATION_CANDIDATE_INVALID")
    return PlacementSearch(kind, side=side if kind == "adjacent" else None,
                           max_positions=max_positions,
                           max_inline_em=float(max_inline_em) if max_inline_em is not None else None)


def _parse_obstacles(raw: Mapping[str, Any], *, search_kind: str) -> PlacementObstacles:
    classes = raw.get("classes")
    if (not isinstance(classes, (list, tuple)) or not classes
            or not all(isinstance(item, str) for item in classes) or len(set(classes)) != len(classes)):
        raise ValueError("E_PRESENTATION_CANDIDATE_INVALID")
    if search_kind in {"nearest-free"} and not _MANDATORY_PLOT_CLASSES.issubset(classes):
        raise ValueError("E_PRESENTATION_CANDIDATE_INVALID")
    return PlacementObstacles(tuple(classes))


def _parse_connector(raw: Mapping[str, Any]) -> PlacementConnector:
    kind = raw.get("kind")
    if kind not in CONNECTOR_KINDS:
        raise ValueError("E_PRESENTATION_CANDIDATE_INVALID")
    return PlacementConnector(kind)


def parse_candidate(raw: Mapping[str, Any]) -> PlacementCandidate:
    """Translate one declared v0.25 ``candidates`` entry into immutable intent.

    This is pure data translation: no geometry, obstacle query or search is
    performed here.  Layout consumes the returned value unchanged.
    """
    candidate_id = raw.get("id")
    if not isinstance(candidate_id, str) or not candidate_id:
        raise ValueError("E_PRESENTATION_CANDIDATE_INVALID")
    region_raw, search_raw, obstacles_raw, connector_raw = (
        raw.get("region"), raw.get("search"), raw.get("obstacles"), raw.get("connector"))
    if not all(isinstance(item, Mapping) for item in (region_raw, search_raw, obstacles_raw, connector_raw)):
        raise ValueError("E_PRESENTATION_CANDIDATE_INVALID")
    search = _parse_search(search_raw)
    connector = _parse_connector(connector_raw)
    if connector.kind == "tail" and search.kind not in {"nearest-free", "adjacent"}:
        raise ValueError("E_PRESENTATION_CANDIDATE_INVALID")
    return PlacementCandidate(candidate_id, _parse_region(region_raw), search,
                              _parse_obstacles(obstacles_raw, search_kind=search.kind), connector)


def parse_candidates(raw: Any) -> tuple[PlacementCandidate, ...]:
    """Translate one annotation's declared ``candidates`` array, unique IDs only."""
    if not isinstance(raw, (list, tuple)) or not raw:
        raise ValueError("E_PRESENTATION_CANDIDATE_INVALID")
    candidates = tuple(parse_candidate(item) for item in raw)
    ids = tuple(candidate.candidate_id for candidate in candidates)
    if len(set(ids)) != len(ids):
        raise ValueError("E_PRESENTATION_CANDIDATE_INVALID")
    return candidates
