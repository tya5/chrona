"""Deterministic renderer-neutral routing used while building a presentation Scene."""
from __future__ import annotations

from heapq import heappop, heappush


def place_relation_route(*, source_port: tuple[float, float], target_port: tuple[float, float],
                         obstacles: tuple[tuple[float, float, float, float], ...],
                         bounds: tuple[float, float, float, float]) -> tuple[tuple[float, float], ...]:
    """Complete one dependency route before Scene projects a path primitive."""
    return route_orthogonal(source_port, target_port, obstacles, bounds=bounds)


def route_orthogonal(start: tuple[float, float], end: tuple[float, float],
                     obstacles: tuple[tuple[float, float, float, float], ...], *,
                     grid_offset: float = 2.0, bend_penalty: float = 12.0,
                     limit: int = 4096,
                     bounds: tuple[float, float, float, float] | None = None) -> tuple[tuple[float, float], ...]:
    """Return the stable shortest orthogonal route on a finite visibility grid."""
    xs_set = {start[0], end[0], *(value for box in obstacles for value in (box[0] - grid_offset, box[2] + grid_offset))}
    ys_set = {start[1], end[1], *(value for box in obstacles for value in (box[1] - grid_offset, box[3] + grid_offset))}
    if bounds is not None:
        left, top, right, bottom = bounds
        xs_set = {value for value in xs_set if left <= value <= right} | {left, right, start[0], end[0]}
        ys_set = {value for value in ys_set if top <= value <= bottom} | {top, bottom, start[1], end[1]}
    xs, ys = sorted(xs_set), sorted(ys_set)
    source = (xs.index(start[0]), ys.index(start[1]), -1)
    target = (xs.index(end[0]), ys.index(end[1]))

    def clear(a: tuple[float, float], b: tuple[float, float]) -> bool:
        for left, top, right, bottom in obstacles:
            if a[1] == b[1] and top < a[1] < bottom and max(a[0], b[0]) > left and min(a[0], b[0]) < right:
                return False
            if a[0] == b[0] and left < a[0] < right and max(a[1], b[1]) > top and min(a[1], b[1]) < bottom:
                return False
        return True

    def heuristic(state: tuple[int, int, int]) -> float:
        return abs(xs[state[0]] - end[0]) + abs(ys[state[1]] - end[1])

    costs, parents, queue = {source: 0.0}, {}, [(heuristic(source), 0.0, source)]
    finish = None
    visited = 0
    while queue:
        _, cost, state = heappop(queue)
        if cost != costs[state]:
            continue
        visited += 1
        if visited > limit:
            raise ValueError("E_PRESENTATION_ROUTE_LIMIT")
        i, j, direction = state
        if (i, j) == target:
            finish = state
            break
        for ni, nj, next_direction in ((i - 1, j, 0), (i + 1, j, 0), (i, j - 1, 1), (i, j + 1, 1)):
            if not (0 <= ni < len(xs) and 0 <= nj < len(ys)):
                continue
            a, b = (xs[i], ys[j]), (xs[ni], ys[nj])
            if not clear(a, b):
                continue
            new_cost = cost + abs(a[0] - b[0]) + abs(a[1] - b[1]) + (bend_penalty if direction not in (-1, next_direction) else 0)
            new_state = (ni, nj, next_direction)
            if new_cost < costs.get(new_state, float("inf")):
                costs[new_state], parents[new_state] = new_cost, state
                heappush(queue, (new_cost + heuristic(new_state), new_cost, new_state))
    if finish is None:
        raise ValueError("E_CONNECTOR_UNROUTABLE")
    path = []
    while True:
        path.append((xs[finish[0]], ys[finish[1]]))
        if finish == source:
            break
        finish = parents[finish]
    path.reverse()
    simplified: list[tuple[float, float]] = []
    for point in path:
        if len(simplified) >= 2:
            first, second = simplified[-2:]
            if first[0] == second[0] == point[0] or first[1] == second[1] == point[1]:
                simplified.pop()
        simplified.append(point)
    return tuple(simplified)
