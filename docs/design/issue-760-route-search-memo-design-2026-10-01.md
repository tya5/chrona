# Issue 760 item 2: route-search memo design

**Status:** Proposed (design for slice I760-2b)
**Refs:** #760 item 2, #687, #721 item 2, #592, #575
**Decision:** the owner approved sharing a route-search memo across the extra
route passes; the gate is byte-identical public output (a no-behaviour-change
proof, per #575).
**Scope:** an internal, output-neutral change to `route_orthogonal`
(`src/chrona/presentation/layout/routing.py`) and `SurfaceObstacleIndex`
(`src/chrona/presentation/layout/obstacles.py`). No public API, Scene, SVG,
diagnostic, schema or specification text changes.

## 1. Baseline (measured, not inferred)

Base `8ed48964`, public slides rendered in process by
`tools.materialize_example.materialize` (the materializer's path). The machine
was heavily shared (load average 170 to 220 on this host), so wall time carries
noise; process CPU time is the steadier figure. Minimum of three back-to-back runs:

| Slide | Wall | Process CPU |
| --- | --- | --- |
| `02-programme-board` | 3.93 s | 1.59 s |
| `16-gallery-editorial-lanes` | 46.7 s | 18.3 s |

Per pass (a profiling wrapper counted `route_orthogonal` calls and time per
pass, and keyed each call by the exact selected obstacle content plus all
arguments to find searches repeated across passes; CPU seconds from one run):

| Pass (`plan_lane_route_reservations` and the real phases) | 02: calls / CPU | 16: calls / CPU |
| --- | --- | --- |
| rehearsal 1: names then routes, no reservations | 43 / 0.35 s | 70 / 6.6 s |
| reference routes, no names (cheap: no names to dodge) | 24 / 0.01 s | 25 / 0.18 s |
| rehearsal 2: names then routes, with the reserved corridors | 32 / 0.21 s | 54 / 4.3 s |
| real routes (after the real names) | 32 / 0.19 s | 70 / 6.5 s |
| calls in the real pass identical to an earlier pass | 32 of 32 | 70 of 70 |
| calls in any other pass identical to an earlier pass | 0 | 0 |

The real pass repeats a rehearsal exactly: on slide 02 the plan is accepted, so the
real index equals rehearsal 2; on slide 16 the plan is rejected (empty), so the
real index equals rehearsal 1. Either way every search of the real pass is a
repeat. Rehearsals 1 and 2 share nothing, because their placed member names
differ. The attainable saving is therefore the real pass: about a third of slide
16's route cost (about 1.5x) and about an eighth of slide 02's. Skipping the real
pass by re-using the rehearsal's batch would save the same searches, but it
changes the phase contract of #592 and is not what the owner approved.

## 2. What `route_orthogonal` reads

With a `SurfaceObstacleIndex`, the result is a pure function of:

1. `start`, `end`, `grid_offset`, `bend_penalty`, `limit`, `bounds`;
2. `port_ids` (exempted obstacle ids; every id must exist and be class `port`,
   else `collisions` raises `E_LAYOUT_OBSTACLE_EXEMPTION_INVALID`);
3. the selection `(classes, regions)` and the **content of that selection** only:
   the grid axes come from `index.select(classes, regions)` envelopes, and every
   `clear()` is `index.collisions(..., classes, regions, port_ids)`, which reads
   only that selection (its `placement_id`, geometry, per-item clearance) and the
   exemption ids. Obstacles outside the selection (for example dependency
   routes, ports and `route-reserve` corridors under the lane route classes
   `mark`, `text`, `label-visual`) are never read.

There is no hidden mutable input: `SurfaceObstacle`, `ObstacleRect` and
`ObstacleSegment` are frozen; `_PreparedSelection` caches and the grid are
performance state that only narrows the candidates the unchanged predicates
see (#721); the search has no randomness, clock or global state; ties are broken
by the `(f, h, cost, state)` heap key and the fixed neighbour order.

## 3. Memo key and why a hit equals a fresh search

Key = `(selection content id, exact argument key)`:

* **Selection content id.** The tuple of one exact key per selected obstacle in
  `select()` order (sorted `placement_id`). An obstacle's exact key is the
  `repr` of the obstacle (class, region, clearance, host, geometry): `repr`
  round-trips floats, so it distinguishes `0.0` from `-0.0` and any one-ulp
  difference, which `==` and `hash` would not. The tuple is interned to a small
  integer by a dict, so equality is by value and there is no hash-collision
  risk (a dict compares keys on a hash match).
* **Exact argument key.** `repr((start, end, grid_offset, bend_penalty, limit,
  bounds))` plus `port_ids` and the selection as `(frozenset | None,
  frozenset | None)`. `repr` keeps `-0.0` apart from `0.0` (the route's returned
  coordinates could differ in sign) and `1` from `1.0`; a missed hit is only a
  slower search, never a wrong one.

A hit returns the stored tuple of points, or re-raises `RouteSearchFailure` with
the stored message (the expensive limit and unroutable searches are memoised
too). Both were produced by the same function on equal inputs, so they are
byte-for-byte what a fresh search returns: the float operations are the ones the
fresh search ran once; the memo performs none. Searches that raise anything
other than `RouteSearchFailure`, and any call with an invalid `port_ids` id,
bypass the memo and run fresh, so error behaviour is unchanged.

## 4. Where it lives (#592 ownership)

The one shared mutable obstacle index stays the only shared mutable state. The
memo is a private part of that index, not a second shared object and not a
module global:

* `SurfaceObstacleIndex()` creates a private `_RouteMemo`.
* `SurfaceObstacleIndex.copy()` (the planning dry run) hands the clone the **same**
  memo object. The memo is only a value-keyed cache of pure results, so sharing
  it between a lineage's indexes cannot change any index's content or any
  result: a lookup is answered by the selection content, never by which index
  asked. This is the sharing the owner decision asks for.
* No typed context gains a field; `LaneRoutePlanContext`, `SurfaceRoutesContext`
  and every phase signature are unchanged. A new `SurfaceObstacleIndex()` (the
  annotation candidate search builds one per candidate) has its own empty memo.
* The memo dies with the root index when the composition ends.

Invalidation is by construction: there is none to perform. An index mutation
(`add`, including route registration between relations and the reserved
corridors) changes the content id of every selection it matches; a selection it
does not match keeps its id, and a cached result for it stays correct because
that content is unchanged. The memo never stores a pointer to an index.

## 5. Memory and cost bound

* Entries: at most `ROUTE_MEMO_LIMIT = 4096` results; once full, new results
  are computed but not stored (deterministic, no eviction order to reason about).
  A search result is a short point tuple.
* Interned selection contents: at most 256 distinct ids; beyond it a selection
  content is not interned and the search runs fresh. Typical use is a handful
  (one per route class set per mutation epoch of a lineage).
* Per query cost: the content tuple is built once per `_PreparedSelection` (which
  `add` already invalidates), so a lookup costs one dict probe plus a `repr` of
  six small values, against a search of 10 to 500 ms.

## 6. Risks

| Risk | Handling |
| --- | --- |
| A key that omits an input returns a stale route | The equivalence test includes a case that MUST differ for every input (endpoints, each limit, `bounds`, `port_ids`, selection, an obstacle moved by one ulp, `-0.0`); a mutation check drops one key part per run and the test fails. |
| Sharing a memo across `copy()` leaks one pass into another | Entries are keyed by selection content; a lookup on a differing index misses. The test runs interleaved copies with divergent obstacles. |
| Subclass overrides `collisions` (the `NaiveIndex` of the #721 test) | The memo lives on each root index, so a subclass lineage never shares with the production one; the test uses distinct lineages. |
| Windows float drift | The memo only replays a result the same machine already computed in the same run; no arithmetic is added or reordered. |
| Exceptions | Only success and `RouteSearchFailure` are cached. |

## 7. Proof plan

1. `test_route_memo_equivalence.py`: for generated and corpus-shaped search inputs
   (the #721 generator plus boundary and ulp cases), the memoised result equals
   the result of a fresh index (empty memo) and of a memo-disabled call, hit and
   miss, success and failure, repeated and with copies that diverge by one
   obstacle; every "key must differ" case asserts a miss and the fresh value.
2. Mutation check (recorded in the PR): remove each key component in turn
   (selection content, `port_ids`, `bounds`, `limit`, `-0.0` distinction) and
   confirm the test fails; restore.
3. Byte identity: `tools.derived_evidence --check` and
   `tools.regenerate_public_examples --check` with no derived change; the
   diagnostic inventory may report stale line numbers because the source edit
   shifts them (CI's derived-sync regenerates it), and nothing else differs.
4. Focused routing, lane, composer and surface wiring tests and
   `tests/unit/chrona/presentation`.
5. Report slide 16 and 02 render times before and after (minimum of three, wall
   and CPU, load stated). If slide 16 improves by under about 1.5x, say so and
   name the remaining cost (rehearsals 1 and 2, which share no search).
