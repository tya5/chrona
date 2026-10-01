# Issue 721 item 2: routing performance design

**Status:** Proposed (design for slice I721-2b)
**Refs:** #721 item 2, #657
**Scope:** an internal, output-neutral refactor of
`SurfaceObstacleIndex.collisions` (`src/chrona/presentation/layout/obstacles.py`).
No public API, Scene, SVG, diagnostic, schema or specification text changes.

## 1. Baseline (measured, not inferred)

Command (profile driver kept out of the repository; it renders the HALCYON board
with the `mission-light` catalogue preset exactly as
`test_cli_margin_days_produces_no_axis_warning_on_halcyon_for_every_catalogue_preset`
does, in process, under `cProfile`):

```
chrona preset copy mission-light --output <tmp>/mission-light      # then margin 7 days, thin-with-record
chrona render examples/halcyon-1/project.yaml --actual examples/halcyon-1/actual.yaml \
       --preset <tmp>/mission-light/preset.yaml --output o.svg --emit-scene o.scene.json
python -c "cProfile.Profile().runcall(main)"; pstats sorted by cumulative
```

| Measure (mission-light, base 44804ebd) | Value |
| --- | --- |
| Total time under cProfile | 195.4 s (CPU 82 s without the profiler; the machine load average was above 100) |
| `select_lane_relation_route` calls | 24 |
| `route_orthogonal` calls | 115 |
| `route_orthogonal` cumulative | 192.6 s = 98.6 % of the render |
| `clear()` calls | 646,012 |
| `SurfaceObstacleIndex.collisions` calls | 646,228, cumulative 177.6 s (91 %) |
| Obstacles scanned per `collisions` call | about 101 (65.3 M `obstacle_envelope` calls / 646 k) |
| Calls reaching the exact `_intersects` predicate | 74,407 (11 % of calls, 0.8 s in total) |

The 98 % claim in #721 holds. Time inside `collisions` splits as: the per-call
`select()` filter and tuple build 41.9 s (24 %), recomputing
`obstacle_envelope(item.geometry)` for every obstacle on every call 49.0 s
(28 %), the generator and `_envelopes_overlap` 79.7 s, and everything else
(validation, `ObstacleSegment.__post_init__`) about 7 s. The exact geometry
predicate is negligible.

### Where the quadratic cost is

The search is A* over a visibility grid whose axes are seeded by two values per
obstacle (so up to about `2n` by `2n` nodes), expanded to at most `limit`
(4096) nodes, each testing four neighbour segments with `clear()`. Every
`clear()` is a linear scan of all `n` selected obstacles that also rebuilds the
obstacle selection and every obstacle envelope from scratch. The cost is
therefore `nodes x 4 x n x (select + envelope + overlap)`, with nodes growing
with `n`. Obstacles never change during one `route_orthogonal` call, and
change only by `add` between calls, yet nothing is reused.

## 2. Proposed structure

Keep `route_orthogonal`, `place_relation_route`, `select_lane_relation_route`
and every `SurfaceObstacleIndex` method signature and return value unchanged.
Change only how `collisions` finds its candidates.

1. **Cached selection.** `SurfaceObstacleIndex` keeps a private map from
   `(classes, regions)` (each `None` or a `frozenset`) to a prepared selection:
   the same tuple `select()` returns today (sorted by `placement_id`), plus a
   per-item tuple of `(envelope, clearance)`. `add` clears the map. Obstacles
   and their geometry are frozen dataclasses, so a cached envelope cannot go
   stale.
2. **Uniform grid over envelopes.** A selection with enough obstacles builds,
   lazily on a repeated query, a uniform grid keyed by cell. Each item is
   registered in every cell its envelope, widened by the item's clearance and a
   rounding slack, touches. An item covering too many cells goes in an
   always-checked "wide" list.
3. **Query.** `collisions` computes the candidate envelope exactly as today,
   widens it by `clearance + max item clearance + slack`, gathers the item
   positions from the touched cells plus the wide list, and **sorts the
   positions**. It then applies, to each candidate and in that order, the
   unchanged original tests: the exemption filter, `_envelopes_overlap` with
   `clearance + item.clearance`, and `_intersects`.

The grid is a conservative pre-filter: it can only remove obstacles that the
original `_envelopes_overlap` would also have rejected. It never decides a
collision.

## 3. Why the considered obstacle set, and every route, is unchanged

* **Same universe.** The selected tuple is the same `select()` result (same
  filter, same sorted order). The grid only narrows it.
* **Same predicate on every survivor.** The exemption test, `_envelopes_overlap`
  and `_intersects` are called with identical arguments, so floating-point
  comparisons are the same operations in the same order. The index never
  re-expresses `left <= right + (clearance + item.clearance)` as a different
  float expression; the slack is only used for the coarse cell range.
* **Conservative cells.** Cell index `floor((v - origin) / size)` is monotone
  non-decreasing in `v` for IEEE doubles. Query and registration intervals are
  both widened by a slack larger than any rounding error of
  `right + clearance`, so any pair accepted by the exact float test shares a
  cell on both axes. Equal intervals touching only at a boundary (`<=`) are
  covered by the slack.
* **Same result order.** The original returns obstacles in the sorted
  `placement_id` order. Candidate positions are sorted before filtering, so the
  returned tuple is element-for-element identical. `egress_collisions` and every
  caller consume that tuple unchanged.
* **Same validation and errors.** The clearance, `host_id`, `rule_host_id` and
  `port_ids` checks run before the query, in the same order, raising the same
  codes. Skipping them when no exemption is given is not a behaviour change,
  because the checks cannot fail on an empty exemption set.
* **Route search untouched.** `route_orthogonal` keeps its grid seeding, A*
  expansion order, `(f, h, cost, state)` heap key, bend penalty, limit and path
  simplification. Because `clear()` returns the same booleans, the heap is fed
  the same sequence, so routes, bends, tie-breaks, `E_PRESENTATION_ROUTE_LIMIT`
  versus `E_CONNECTOR_UNROUTABLE`, and the lane quality rejections stay
  identical.

## 4. Order-of-iteration and float risks

| Risk | Handling |
| --- | --- |
| Result order of `collisions` depends on iteration order | Sort grid candidate positions; the test compares the full tuple, not a set. |
| `classes` and `regions` are `Iterable` (possibly a generator) | Convert each to a `frozenset` once, as `select()` does now. |
| Per-item clearance differs from the query clearance | Register with the item's own clearance; query with `clearance + max_item_clearance`; the exact test still uses `clearance + item.clearance`. |
| Float rounding at an envelope boundary (`<=`) | Coarse slack plus the unchanged exact test; the property test includes boundary-exact and ulp-adjacent cases. |
| Cell arithmetic at negative coordinates | Origin is the minimum registered coordinate and `floor` is used, not `int()` truncation. |
| Obstacles added between queries | `add` invalidates the cache; the index is monotone, so rebuilds are rare (about one per accepted route). |
| `SurfaceObstacleIndex` built fresh per candidate (annotation search) | The grid is built only after a selection is queried repeatedly; the first queries use the cached linear scan, so a one-shot index costs no more than today. |
| Platform float differences | No new arithmetic on values that reach geometry; only comparisons and `floor` on the same doubles. No fused operations. |

## 5. Proof plan

1. **Property test** (`tests/unit/chrona/presentation/layout/test_obstacle_index_equivalence.py`):
   for seeded generated obstacle sets (rectangles and stroked segments, mixed
   classes, regions and clearances, duplicates of coordinates, touching,
   overlapping, zero-extent query boxes, boundary-exact, negative and large
   coordinates, float-rounding offsets) and generated query geometries and
   exemption arguments, the indexed `collisions` equals a naive reference scan
   (the pre-change implementation transcribed into the test) as full ordered
   tuples, on both the linear and the grid path. A mutation check (narrow the
   query bounds on a worktree copy, see the test fail, restore) is recorded in
   the PR.
2. **Byte identity:** `python -m tools.derived_evidence --check` and
   `python -m tools.regenerate_public_examples --check` report no derived
   change. Any changed Scene or SVG stops the slice.
3. **Focused tests:** routing, lane and composer tests and
   `tests/unit/chrona/presentation`.
4. **Timing:** one HALCYON preset render and the slowest corpus tests, before
   and after, same command, same machine, three runs each, minimum reported,
   with the machine load stated. The expected gain is bounded by the remaining
   non-index cost (`ObstacleSegment` construction, A* bookkeeping); if the
   HALCYON render improves less than about 2x, the report says so.

## 6. Non-goals

Reducing the number of `clear()` calls (for example a smaller visibility grid
or pruning A* nodes) can change which of several equal-cost routes is chosen and
is a behaviour change; it is out of scope and would need its own design.
