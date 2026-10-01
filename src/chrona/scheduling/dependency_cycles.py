"""Find the dependency cycles the reference scheduler cannot place (#780).

Spec 04 section 16 does not call a graph cycle an error: a loop with a zero or negative lag can be
satisfiable, and an implementation limited to an acyclic subset must report a cycle it cannot place as
a capability limitation (``E_UNSUPPORTED_CYCLE``, or ``E_UNSATISFIABLE_DEPENDENCIES`` for a positive
calendar-day loop). This module is that check as a pure function of a Project that Core validation
accepted, so ``validate`` and ``schedule`` can report the same finding before any date is computed.

Two checks, each returning strongly connected sets:

1. *Wait cycle*, exactly the scheduler's stall. A non-fixed object waits for the placement of the source
   object of every relation that targets it, and a rollup waits for its children; fixed objects never
   wait. Objects that merely sit downstream of such a cycle are not part of it.
2. *Endpoint loop through a fixed object.* Nodes are ``(object, endpoint)``; edges are the relations with
   a non-negative lag plus ``start -> end`` of every span. A fixed object never waits, so check 1 cannot
   see a loop through it (the scheduler reports only a date symptom, ``E_FIXED_TARGET_VIOLATION``); a
   loop of non-negative relations is satisfiable only if every date on it is equal. A negative lag breaks
   the loop, because such a loop can be satisfiable and the date check decides.

Nothing here reads a calendar or computes a date.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Hashable, Iterable, Mapping

from chrona.core.diagnostics import Diagnostic
from chrona.core.temporal import TemporalError, parse_amount
from chrona.scheduling.scheduler import _has_positive_dependency_cycle

_FIXED = frozenset({"fixed-point", "fixed-span"})
_SPANS = frozenset({"scheduled", "fixed-span", "rollup"})


@dataclass(frozen=True)
class DependencyCycle:
    """One cycle: its objects in Project order and the relation (by index) declared last inside it."""

    objects: tuple[str, ...]
    closing_relation: int
    unsatisfiable: bool

    def diagnostic(self) -> Diagnostic:
        code = "E_UNSATISFIABLE_DEPENDENCIES" if self.unsatisfiable else "E_UNSUPPORTED_CYCLE"
        return Diagnostic(
            code,
            f"Dependency cycle among {', '.join(self.objects)}; the relation at this path closes it. "
            "Objects that wait on each other cannot be scheduled: remove or redirect one relation in the cycle",
            f"/relations/{self.closing_relation}",
        )


def dependency_cycle_diagnostics(project: Mapping[str, Any]) -> tuple[Diagnostic, ...]:
    return tuple(cycle.diagnostic() for cycle in find_dependency_cycles(project))


def find_dependency_cycles(project: Mapping[str, Any]) -> tuple[DependencyCycle, ...]:
    objects: Mapping[str, Any] = project.get("objects", {})
    relations: list[Mapping[str, Any]] = list(project.get("relations", []))
    order = {object_id: position for position, object_id in enumerate(objects)}
    mode = {object_id: item["schedule"]["mode"] for object_id, item in objects.items()}

    found: list[tuple[frozenset[str], set[int]]] = []

    waits: dict[str, list[str]] = {object_id: [] for object_id in objects}
    wait_edges: dict[tuple[str, str], set[int]] = {}
    for index, relation in enumerate(relations):
        source, target = relation["from"]["object"], relation["to"]["object"]
        if mode[target] in _FIXED:
            continue
        if source not in waits[target]:
            waits[target].append(source)
        wait_edges.setdefault((target, source), set()).add(index)
    for object_id, item in objects.items():
        parent = item.get("parent")
        if parent in waits and mode[parent] == "rollup" and object_id not in waits[parent]:
            waits[parent].append(object_id)
    for component in _cycles(list(objects), waits):
        members = frozenset(component)
        inside = {index for (target, source), indexes in wait_edges.items() if target in members and source in members
                  for index in indexes}
        found.append((members, inside))

    nodes: list[tuple[str, str]] = []
    successors: dict[tuple[str, str], list[tuple[str, str]]] = {}
    relation_edges: dict[tuple[tuple[str, str], tuple[str, str]], set[int]] = {}

    def add_edge(start: tuple[str, str], end: tuple[str, str]) -> None:
        for node in (start, end):
            if node not in successors:
                successors[node] = []
                nodes.append(node)
        if end not in successors[start]:
            successors[start].append(end)

    for object_id in objects:
        if mode[object_id] in _SPANS:
            add_edge((object_id, "start"), (object_id, "end"))
    for index, relation in enumerate(relations):
        if _is_negative(relation.get("lag", "0d")):
            continue
        start = (relation["from"]["object"], relation["from"]["endpoint"])
        end = (relation["to"]["object"], relation["to"]["endpoint"])
        add_edge(start, end)
        relation_edges.setdefault((start, end), set()).add(index)
    for component in _cycles(nodes, successors):
        members = frozenset(object_id for object_id, _endpoint in component)
        inside = {index for (start, end), indexes in relation_edges.items() if start in component and end in component
                  for index in indexes}
        if not inside or not any(mode[object_id] in _FIXED for object_id in members):
            continue
        if any(members <= already for already, _ in found):
            continue
        found.append((members, inside))

    cycles = []
    for members, inside in found:
        ordered = tuple(sorted(members, key=order.__getitem__))
        carrying = [relations[index] for index in sorted(inside)]
        cycles.append(DependencyCycle(ordered, max(inside), _has_positive_dependency_cycle({"relations": carrying})))
    return tuple(sorted(cycles, key=lambda cycle: order[cycle.objects[0]]))


def _is_negative(lag: Any) -> bool:
    amount = lag if isinstance(lag, str) else lag["value"]
    try:
        return any(number < 0 for number, _unit in parse_amount(amount))
    except TemporalError:
        return False


def _cycles(nodes: Iterable[Hashable], successors: Mapping[Any, list[Any]]) -> list[frozenset[Any]]:
    """Strongly connected sets that hold a loop (more than one node, or a node that follows itself)."""
    index_of: dict[Any, int] = {}
    low: dict[Any, int] = {}
    on_stack: set[Any] = set()
    stack: list[Any] = []
    result: list[frozenset[Any]] = []
    counter = 0
    for root in nodes:
        if root in index_of:
            continue
        work = [(root, iter(successors.get(root, ())))]
        index_of[root] = low[root] = counter
        counter += 1
        stack.append(root)
        on_stack.add(root)
        while work:
            node, pending = work[-1]
            advanced = False
            for follower in pending:
                if follower not in index_of:
                    index_of[follower] = low[follower] = counter
                    counter += 1
                    stack.append(follower)
                    on_stack.add(follower)
                    work.append((follower, iter(successors.get(follower, ()))))
                    advanced = True
                    break
                if follower in on_stack:
                    low[node] = min(low[node], index_of[follower])
            if advanced:
                continue
            work.pop()
            if work:
                parent = work[-1][0]
                low[parent] = min(low[parent], low[node])
            if low[node] == index_of[node]:
                component = []
                while True:
                    member = stack.pop()
                    on_stack.discard(member)
                    component.append(member)
                    if member == node:
                        break
                if len(component) > 1 or node in successors.get(node, ()):
                    result.append(frozenset(component))
    return result
