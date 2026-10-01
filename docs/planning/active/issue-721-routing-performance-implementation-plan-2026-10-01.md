# Issue 721 item 2: routing performance implementation plan

**Status:** Active
**Design:** [issue-721-routing-performance-design-2026-10-01.md](../../design/issue-721-routing-performance-design-2026-10-01.md)
**Review:** [issue-721-routing-performance-architecture-review-2026-10-01.md](../../reviews/current/issue-721-routing-performance-architecture-review-2026-10-01.md)
**Refs:** #721 (item 2 only; items 1 and 3 belong to other work)

## Literal acceptance for item 2 (from the issue body)

"About 98% of a HALCYON preset render is `presentation/layout/routing.py::route_orthogonal`
... A spatial index over obstacles would cut the dominant cost of the corpus tests and of
every render. It is a product change with byte identity as the proof."

Working acceptance: the dominant cost is reduced; every committed Scene and SVG is
byte-identical; the speedup is reported honestly.

## Slices

| Slice | Content | Files | Publication |
| --- | --- | --- | --- |
| I721-2a | Profile, design, architecture review, this plan | the three docs | docs PR, merged first |
| I721-2b | Cached selection and grid pre-filter behind `SurfaceObstacleIndex.collisions`; property test; timings | `src/chrona/presentation/layout/obstacles.py`, `tests/unit/chrona/presentation/layout/test_obstacle_index_equivalence.py`, this plan's evidence section | code PR |

Further slices (a different hot path found after 2b, for example the remaining A*
bookkeeping) are not planned; they are proposed only if the 2b profile shows a new
dominant cost, and any change to the number or order of `clear()` calls needs its own
design because it can change routes.

## I721-2b work items

1. Prepared selection cache keyed by `(frozenset|None, frozenset|None)`, cleared by `add`.
2. Lazy uniform-grid pre-filter after repeated queries of one selection; wide-item list.
3. `collisions` keeps validation and the exact `_envelopes_overlap` and `_intersects`
   tests; candidates are visited in sorted-position order.
4. Property test against a transcribed naive reference, both paths, with the mutation
   check described in the design.

## Gates for I721-2b

* New property test passes; mutation check fails the test and is restored.
* `python -m tools.derived_evidence --check` and
  `python -m tools.regenerate_public_examples --check` pass with no derived change.
* Focused routing, lane and composer tests; `tests/unit/chrona/presentation`.
* Before and after timing of one HALCYON preset render and the slowest corpus tests
  (same command, same machine, three runs, minimum, load stated).
* PR body notes that a source edit shifts line numbers, so CI's derived-sync may
  regenerate line-number-derived docs after merge; the PR edits none of them.
* If any committed Scene or SVG changes: stop, report the primitive and the cause, do not
  regenerate or merge.

## Evidence

Baseline profile: see the design document section 1. Slice results are added here after
2b merges.
