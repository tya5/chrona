"""The route-search memo returns exactly what a fresh search returns (#760 item 2).

The reference is `routing._search_orthogonal`, the unmemoised search body that
`route_orthogonal` ran before the memo. Every comparison is exact (`==` on point tuples plus
`repr`, so `-0.0` and `0.0` are told apart), over generated indexes, over index copies that
diverge, and over the real searches of a public slide. Each "key must differ" case also
asserts that the memo did not answer it from another case, and the mutation test breaks the
key one component at a time and shows this suite's comparison catches it.
"""
from __future__ import annotations

from math import nextafter
from pathlib import Path
from random import Random

import pytest

from chrona.presentation.layout import routing
from chrona.presentation.layout.obstacles import (
    ObstacleRect, ObstacleSegment, ROUTE_MEMO_LIMIT, SurfaceObstacle, SurfaceObstacleIndex,
)
from chrona.presentation.layout.routing import RouteSearchFailure, route_orthogonal

CLASSES = ("mark", "text", "label-visual", "dependency-route", "port")
REGIONS = ("timeline", "group-header")
ROUTE_CLASSES = ("mark", "text", "label-visual")
BOUNDS = (-12.0, -12.0, 40.0, 40.0)


def outcome(call) -> tuple:
    """The result or the failure message, with reprs so signed zeros differ."""
    try:
        return ("route", repr(call()))
    except RouteSearchFailure as failure:
        return ("failure", str(failure))


def fresh(index, start, end, **kwargs) -> tuple:
    """The pre-memo search: same arguments, no memo involved."""
    arguments = dict(grid_offset=routing.ROUTE_GRID_OFFSET, bend_penalty=12.0, limit=4096, bounds=None,
                     port_ids=(), classes=None, regions=None)
    arguments.update(kwargs)
    return outcome(lambda: routing._search_orthogonal(start, end, index, **arguments))


def memoised(index, start, end, **kwargs) -> tuple:
    return outcome(lambda: route_orthogonal(start, end, index, **kwargs))


def lattice(rng: Random) -> float:
    base = float(rng.randint(-4, 24))
    kind = rng.randrange(5)
    if base == 0.0:
        return base  # a denormal offset from zero is a degenerate segment the predicates never see
    return nextafter(base, float("inf")) if kind == 0 else nextafter(base, float("-inf")) if kind == 1 else base


def random_obstacle(rng: Random, number: int) -> SurfaceObstacle:
    x, y = lattice(rng), lattice(rng)
    if rng.random() < 0.6:
        geometry = ObstacleRect(x, y, x + rng.randint(1, 6), y + rng.randint(1, 6))
    else:
        length = rng.randint(1, 9)
        end = (x + length, y) if rng.random() < 0.5 else (x, y + length)
        geometry = ObstacleSegment((x, y), end, stroke_width=rng.choice((0.0, 2.0)))
    return SurfaceObstacle(f"o{number:04d}", rng.choice(CLASSES), rng.choice(REGIONS), geometry,
                           clearance=rng.choice((0.0, 0.0, 0.5)))


def random_index(rng: Random, count: int) -> SurfaceObstacleIndex:
    index = SurfaceObstacleIndex()
    for number in range(count):
        index.add(random_obstacle(rng, number))
    index.add(SurfaceObstacle("port:p", "port", "timeline", ObstacleRect(0.0, 0.0, 0.02, 0.02)))
    return index


def random_search(rng: Random) -> dict:
    return {"bounds": BOUNDS, "limit": rng.choice((50, 600, 4096)),
            "classes": rng.choice((None, ROUTE_CLASSES, ("mark",))),
            "regions": rng.choice((None, REGIONS, ("timeline",))),
            "port_ids": rng.choice(((), ("port:p",)))}


@pytest.mark.parametrize("count", [0, 4, 12, 30, 60])
def test_memoised_equals_fresh_on_first_and_repeated_calls(count: int) -> None:
    rng = Random(f"memo:{count}")
    compared = failures = hits = 0
    for case in range(25):
        index = random_index(rng, count)
        for _ in range(4):
            start, end = (lattice(rng), lattice(rng)), (lattice(rng), lattice(rng))
            if start == end:
                continue
            search = random_search(rng)
            expected = fresh(index, start, end, **search)
            memo = index._route_memo
            stored = len(memo.results)
            first = memoised(index, start, end, **search)
            second = memoised(index, start, end, **search)
            assert first == second == expected, (case, start, end, search)
            hits += len(memo.results) == stored + 1 or len(memo.results) == stored  # stored once, or already known
            compared += 1
            failures += expected[0] == "failure"
    assert compared >= 80 and hits == compared
    assert failures > 0 or count == 0  # failures are memoised and replayed too


def test_a_hit_is_actually_served_from_the_memo(monkeypatch) -> None:
    index = random_index(Random("served"), 20)
    start, end = (0.0, 0.0), (20.0, 18.0)
    first = memoised(index, start, end, bounds=BOUNDS)
    monkeypatch.setattr(routing, "_search_orthogonal", lambda *a, **k: pytest.fail("a hit must not search"))
    assert memoised(index, start, end, bounds=BOUNDS) == first
    assert memoised(index.copy(), start, end, bounds=BOUNDS) == first  # a lineage member shares the memo


def test_failures_are_replayed_with_the_same_message() -> None:
    index = SurfaceObstacleIndex()
    index.add(SurfaceObstacle("wall", "mark", "timeline", ObstacleRect(-100.0, 5.0, 100.0, 6.0)))
    for limit, message in ((4096, "E_CONNECTOR_UNROUTABLE"), (3, "E_PRESENTATION_ROUTE_LIMIT")):
        search = dict(bounds=(-1.0, -1.0, 1.0, 10.0), limit=limit, classes=ROUTE_CLASSES)
        expected = fresh(index, (0.0, 0.0), (0.0, 9.0), **search)
        assert expected == ("failure", message)
        assert memoised(index, (0.0, 0.0), (0.0, 9.0), **search) == expected
        assert memoised(index, (0.0, 0.0), (0.0, 9.0), **search) == expected


@pytest.mark.parametrize("seed", range(3))
def test_copies_that_diverge_never_share_an_answer(seed: int) -> None:
    """The planning rehearsals: copies of one index, each gaining different obstacles, share one memo."""
    rng = Random(f"copies:{seed}")
    base = random_index(rng, 25)
    copies = [base.copy() for _ in range(4)]
    for number, copy in enumerate(copies):
        for extra in range(number * 2):
            copy.add(random_obstacle(rng, 1000 + number * 10 + extra))
    for _ in range(25):
        start, end = (lattice(rng), lattice(rng)), (lattice(rng), lattice(rng))
        if start == end:
            continue
        search = random_search(rng)
        for index in (*copies, base, base.copy()):  # interleaved, repeated, some identical to one another
            assert memoised(index, start, end, **search) == fresh(index, start, end, **search)


def mutations() -> list[tuple[str, dict]]:
    """Pairs of searches that differ in exactly one input; the memo must not confuse them."""
    return [("start", dict(start=(0.0, 0.0), other_start=(1.0, 0.0))),
            ("end", dict(end=(20.0, 18.0), other_end=(20.0, 17.0))),
            ("limit", dict(limit=2, other_limit=4096)),
            ("bounds", dict(bounds=BOUNDS, other_bounds=(-12.0, -12.0, 40.0, 4.0))),
            ("grid_offset", dict(grid_offset=2.0, other_grid_offset=3.0)),
            ("bend_penalty", dict(bend_penalty=12.0, other_bend_penalty=0.0)),
            ("classes", dict(classes=("mark",), other_classes=("mark", "text"))),
            ("regions", dict(regions=("timeline",), other_regions=("timeline", "group-header"))),
            ("port_ids", dict(port_ids=(), other_port_ids=("port:p",)))]


def pair_outcomes(name: str, parameters: dict, index: SurfaceObstacleIndex) -> tuple[tuple, tuple, tuple, tuple]:
    defaults = dict(start=(0.0, 0.0), end=(20.0, 18.0), limit=4096, bounds=BOUNDS, grid_offset=2.0,
                    bend_penalty=12.0, classes=ROUTE_CLASSES, regions=REGIONS, port_ids=())
    first = {**defaults, **{key: value for key, value in parameters.items() if not key.startswith("other_")}}
    second = {**first, name: parameters[f"other_{name}"]}
    def call(arguments, runner):
        arguments = dict(arguments)
        start, end = arguments.pop("start"), arguments.pop("end")
        return runner(index, start, end, **arguments)
    return (call(first, memoised), call(second, memoised), call(first, fresh), call(second, fresh))


def midfield_index() -> SurfaceObstacleIndex:
    index = random_index(Random("differ"), 18)
    index.add(SurfaceObstacle("zz:wall", "mark", "timeline", ObstacleRect(4.0, -3.0, 6.0, 12.0)))
    return index


@pytest.mark.parametrize("name,parameters", mutations(), ids=[name for name, _ in mutations()])
def test_inputs_that_differ_get_their_own_answer(name: str, parameters: dict) -> None:
    index = midfield_index()
    first, second, expected_first, expected_second = pair_outcomes(name, parameters, index)
    assert (first, second) == (expected_first, expected_second)
    # Asked again in the opposite order, still each its own.
    again_second, again_first = (pair_outcomes(name, parameters, index)[1], pair_outcomes(name, parameters, index)[0])
    assert (again_first, again_second) == (expected_first, expected_second)


def test_the_selection_content_is_part_of_the_key() -> None:
    index = midfield_index()
    search = dict(bounds=BOUNDS, classes=ROUTE_CLASSES, regions=REGIONS)
    before = memoised(index, (0.0, 0.0), (20.0, 18.0), **search)
    index.add(SurfaceObstacle("zz:new", "mark", "timeline", ObstacleRect(8.0, -3.0, 10.0, 25.0)))
    after = memoised(index, (0.0, 0.0), (20.0, 18.0), **search)
    assert after == fresh(index, (0.0, 0.0), (20.0, 18.0), **search) and after != before
    # An obstacle outside the selection changes nothing the search reads, and may reuse the answer.
    index.add(SurfaceObstacle("zz:route", "dependency-route", "timeline", ObstacleRect(1.0, 1.0, 2.0, 2.0)))
    assert memoised(index, (0.0, 0.0), (20.0, 18.0), **search) == after


def test_port_exemptions_are_part_of_the_key() -> None:
    index = midfield_index()
    index.add(SurfaceObstacle("port:blocker", "port", "timeline", ObstacleRect(-1.0, -1.0, 30.0, 30.0)))
    results = []
    for port_ids in ((), ("port:blocker",), (), ("port:blocker",)):  # an exemption changes what blocks
        got = memoised(index, (0.0, 0.0), (20.0, 18.0), bounds=BOUNDS, port_ids=port_ids)
        assert got == fresh(index, (0.0, 0.0), (20.0, 18.0), bounds=BOUNDS, port_ids=port_ids)
        results.append(got)
    assert results[0] != results[1]


def test_a_one_ulp_or_signed_zero_difference_is_a_different_key() -> None:
    def build(left: float) -> SurfaceObstacleIndex:
        index = SurfaceObstacleIndex()
        index.add(SurfaceObstacle("a", "mark", "timeline", ObstacleRect(left, 0.0, 6.0, 10.0)))
        return index
    memo_owner = build(4.0)
    first = memoised(memo_owner, (0.0, 5.0), (12.0, 5.0), bounds=BOUNDS)
    moved = memo_owner.copy()
    moved._by_id["a"] = SurfaceObstacle("a", "mark", "timeline", ObstacleRect(nextafter(4.0, 5.0), 0.0, 6.0, 10.0))
    moved._ordered, moved._prepared = None, {}
    assert memoised(moved, (0.0, 5.0), (12.0, 5.0), bounds=BOUNDS) == fresh(
        moved, (0.0, 5.0), (12.0, 5.0), bounds=BOUNDS)
    assert first == fresh(memo_owner, (0.0, 5.0), (12.0, 5.0), bounds=BOUNDS)
    positive = memoised(memo_owner, (0.0, 5.0), (12.0, 5.0), bounds=BOUNDS)
    negative = memoised(memo_owner, (-0.0, 5.0), (12.0, 5.0), bounds=BOUNDS)
    assert positive == fresh(memo_owner, (0.0, 5.0), (12.0, 5.0), bounds=BOUNDS)
    assert negative == fresh(memo_owner, (-0.0, 5.0), (12.0, 5.0), bounds=BOUNDS)


def test_invalid_port_ids_raise_as_before_and_are_not_memoised() -> None:
    index = midfield_index()
    for port_ids in (("missing",), ("zz:wall",)):
        with pytest.raises(ValueError, match="E_LAYOUT_OBSTACLE_EXEMPTION_INVALID"):
            route_orthogonal((0.0, 0.0), (20.0, 18.0), index, bounds=BOUNDS, port_ids=port_ids)
    assert not index._route_memo.results


def test_the_memo_is_bounded_and_a_full_memo_still_answers_correctly() -> None:
    index = midfield_index()
    memo = index._route_memo
    for number in range(ROUTE_MEMO_LIMIT + 5):
        memo.store(("filler", number), ())
    assert len(memo.results) == ROUTE_MEMO_LIMIT
    start, end = (0.0, 0.0), (20.0, 18.0)
    assert memoised(index, start, end, bounds=BOUNDS) == fresh(index, start, end, bounds=BOUNDS)
    assert len(memo.results) == ROUTE_MEMO_LIMIT
    for number in range(256):
        memo.content_id((f"filler{number}",))
    assert memo.content_id(("one more",)) is None and len(memo.contents) == 256
    index.add(SurfaceObstacle("zz:extra", "mark", "timeline", ObstacleRect(30.0, 30.0, 31.0, 31.0)))
    assert index.route_memo_scope(None, None, ()) is None  # a full interning table means: search fresh
    assert memoised(index, start, end, bounds=BOUNDS) == fresh(index, start, end, bounds=BOUNDS)


def test_distinct_lineages_do_not_share() -> None:
    first, second = midfield_index(), midfield_index()
    assert first._route_memo is not second._route_memo
    assert first.copy()._route_memo is first._route_memo


@pytest.mark.parametrize("component", range(6))
def test_mutation_check_a_broken_key_is_caught(monkeypatch, component: int) -> None:
    """Break one key component at a time; the suite's comparison must then see a wrong answer.

    Components: 0 selection content, 1 endpoints, 2 limit, 3 bounds, 4 port_ids, 5 signed zero.
    """
    original = routing._route_memo_key

    def broken(content_id, start, end, grid_offset, bend_penalty, limit, bounds, port_ids, classes, regions):
        if component == 0:
            content_id = 0
        elif component == 1:
            start, end = (0.0, 0.0), (0.0, 0.0)
        elif component == 2:
            limit = 0
        elif component == 3:
            bounds = None
        elif component == 4:
            port_ids = ()
        else:
            start = (abs(start[0]), start[1])
        return original(content_id, start, end, grid_offset, bend_penalty, limit, bounds, port_ids, classes, regions)

    monkeypatch.setattr(routing, "_route_memo_key", broken)
    wrong = 0
    if component == 0:
        index = midfield_index()
        search = dict(bounds=BOUNDS, classes=ROUTE_CLASSES, regions=REGIONS)
        memoised(index, (0.0, 0.0), (20.0, 18.0), **search)
        index.add(SurfaceObstacle("zz:new", "mark", "timeline", ObstacleRect(8.0, -3.0, 10.0, 25.0)))
        wrong += memoised(index, (0.0, 0.0), (20.0, 18.0), **search) != fresh(index, (0.0, 0.0), (20.0, 18.0), **search)
    elif component == 4:
        index = midfield_index()
        index.add(SurfaceObstacle("port:blocker", "port", "timeline", ObstacleRect(0.0, 0.0, 20.0, 18.0)))
        search = dict(bounds=BOUNDS, classes=None, regions=None)
        for port_ids in ((), ("port:blocker",)):
            wrong += (memoised(index, (0.0, 0.0), (20.0, 18.0), port_ids=port_ids, **search)
                      != fresh(index, (0.0, 0.0), (20.0, 18.0), port_ids=port_ids, **search))
    elif component == 5:
        index = midfield_index()
        for start in ((0.0, 5.0), (-0.0, 5.0)):
            wrong += memoised(index, start, (12.0, 5.0), bounds=BOUNDS) != fresh(index, start, (12.0, 5.0), bounds=BOUNDS)
    else:
        for name, parameters in mutations():
            if (component, name) in {(1, "start"), (1, "end"), (2, "limit"), (3, "bounds")}:
                first, second, expected_first, expected_second = pair_outcomes(name, parameters, midfield_index())
                wrong += (first, second) != (expected_first, expected_second)
    assert wrong, f"mutating key component {component} was not detected"


def test_every_real_search_of_a_public_slide_matches_a_fresh_search(monkeypatch, tmp_path: Path) -> None:
    """Corpus-derived inputs: each search the programme-board render makes is re-run unmemoised."""
    from chrona.usecases.materialize import materialize

    root = Path(__file__).resolve().parents[5]
    compared = hits = 0
    original = routing.route_orthogonal

    def checking(start, end, obstacles, **kwargs):
        nonlocal compared, hits
        if isinstance(obstacles, SurfaceObstacleIndex):
            reference = fresh(obstacles, start, end, **kwargs)
            before = len(obstacles._route_memo.results)
            got = outcome(lambda: original(start, end, obstacles, **kwargs))
            assert got == reference
            hits += len(obstacles._route_memo.results) == before
            compared += 1
        return original(start, end, obstacles, **kwargs)

    monkeypatch.setattr(routing, "route_orthogonal", checking)
    materialize(root / "examples" / "halcyon-1" / "manifest.yaml", "programme-board", tmp_path / "out", write=True)
    assert compared >= 100
    assert hits >= 30  # the real pass repeats the accepted rehearsal's searches
