"""Layout-owned staged search domains; terminal fallback is a separate completion."""
from collections.abc import Callable
from dataclasses import dataclass

from chrona.presentation.layout.model import RelationUnroutableMode
from chrona.presentation.layout.obstacles import SurfaceObstacleIndex
from chrona.presentation.layout.ports import ConnectorEgress
from chrona.presentation.layout.routing import RelationRouteSelection
from chrona.presentation.model.info_diagnostics import RelationResolutionStage


@dataclass(frozen=True)
class RelationObstacleDomain:
    stage: RelationResolutionStage
    obstacles: SurfaceObstacleIndex
    required_primary_mark_ids: frozenset[str] | None = None

    @classmethod
    def normal(cls, obstacles: SurfaceObstacleIndex) -> "RelationObstacleDomain":
        return cls(RelationResolutionStage.NORMAL, obstacles)


def relaxed_domain(obstacles: SurfaceObstacleIndex, stage: RelationResolutionStage,
                   endpoint_host_ids: frozenset[str],
                   required_label_obstacle_ids: frozenset[str] = frozenset()) -> RelationObstacleDomain:
    """Filter geometry once, retaining explicit required-label obstacles in staged searches."""
    if not isinstance(stage, RelationResolutionStage):
        raise ValueError("search domain requires a typed resolution stage")
    if stage is RelationResolutionStage.NORMAL:
        return RelationObstacleDomain.normal(obstacles)
    if stage not in {RelationResolutionStage.LABEL_VISUALS,
                     RelationResolutionStage.TEXT, RelationResolutionStage.MARKS}:
        raise ValueError("a terminal fallback is not a search domain")
    filtered = SurfaceObstacleIndex()
    for item in obstacles.all():
        if item.placement_id in required_label_obstacle_ids:
            filtered.add(item)
            continue
        if item.obstacle_class in {"label-visual", "relation-label"}:
            continue
        if item.obstacle_class == "text" and (
                item.placement_id.startswith("relation-label:")
                or stage in {RelationResolutionStage.TEXT, RelationResolutionStage.MARKS}):
            continue
        if (stage is RelationResolutionStage.MARKS and item.obstacle_class == "mark"
                and item.placement_id not in endpoint_host_ids):
            continue
        filtered.add(item)
    return RelationObstacleDomain(stage, filtered,
        endpoint_host_ids if stage is RelationResolutionStage.MARKS else None)


@dataclass(frozen=True)
class RelationRouteAttemptOutcome:
    """One search plus its completed side-entry alternative, without forged search evidence."""

    search_receipt: RelationRouteSelection
    selected_pair: tuple[ConnectorEgress, ConnectorEgress] | None
    points: tuple[tuple[float, float], ...]
    used_back_route: bool = False
    entry_fallback_reason: str = ""

    def __post_init__(self) -> None:
        if ((self.selected_pair is None) != (not self.points)
                or (self.selected_pair is not None and len(self.points) < 2)
                or not isinstance(self.used_back_route, bool)
                or not isinstance(self.entry_fallback_reason, str)
                or (self.used_back_route and self.selected_pair is None)
                or (not self.used_back_route and (
                    self.selected_pair != self.search_receipt.selected_pair
                    or self.points != self.search_receipt.points))):
            raise ValueError("E_LAYOUT_ROUTE_ATTEMPT_INVALID: completed side-entry outcome")


@dataclass(frozen=True)
class StagedRouteAttempt:
    stage: RelationResolutionStage
    selection: RelationRouteSelection | RelationRouteAttemptOutcome

    @property
    def search_receipt(self) -> RelationRouteSelection:
        return (self.selection.search_receipt
                if isinstance(self.selection, RelationRouteAttemptOutcome) else self.selection)


@dataclass(frozen=True)
class RelationSearchResolution:
    """Search evidence, not a claim that terminal geometry has been completed."""

    attempts: tuple[StagedRouteAttempt, ...]
    terminal_fallback: RelationResolutionStage | None = None

    @property
    def accepted(self) -> StagedRouteAttempt | None:
        return next((item for item in self.attempts
                     if item.selection.selected_pair is not None), None)


def search_relation_resolution(mode: RelationUnroutableMode, *,
                              obstacles: SurfaceObstacleIndex,
                              endpoint_host_ids: frozenset[str],
                              required_label_obstacle_ids: frozenset[str] = frozenset(),
                              attempt: Callable[[RelationObstacleDomain],
                                                RelationRouteSelection | RelationRouteAttemptOutcome],
                              ) -> RelationSearchResolution:
    """Invoke one Layout attempt owner; it creates a fresh budget each call.

    The callback stays inside Layout and must use the supplied domain for
    port admission, search, reduction and final validators. This coordinator
    neither measures in Scene nor resets a budget within an attempt.
    """
    if not isinstance(mode, RelationUnroutableMode):
        raise ValueError("search resolution requires a typed Layout mode")
    if mode is RelationUnroutableMode.OVERLAP:
        return RelationSearchResolution((), RelationResolutionStage.OVERLAP)
    if mode is RelationUnroutableMode.STUB:
        return RelationSearchResolution((), RelationResolutionStage.STUB)
    stages = ((RelationResolutionStage.NORMAL,) if mode is RelationUnroutableMode.SUPPRESS
              else (RelationResolutionStage.NORMAL, RelationResolutionStage.LABEL_VISUALS,
                    RelationResolutionStage.TEXT, RelationResolutionStage.MARKS))
    attempts = []
    for stage in stages:
        selected = attempt(relaxed_domain(obstacles, stage, endpoint_host_ids,
                                          required_label_obstacle_ids))
        attempts.append(StagedRouteAttempt(stage, selected))
        if selected.selected_pair is not None:
            return RelationSearchResolution(tuple(attempts))
    return RelationSearchResolution(tuple(attempts),
        RelationResolutionStage.OVERLAP if mode is RelationUnroutableMode.RELAX else None)
