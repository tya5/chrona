# Issue 760 item 2: route-search memo implementation plan

**Status:** Active
**Design:** [issue-760-route-search-memo-design-2026-10-01.md](../../design/issue-760-route-search-memo-design-2026-10-01.md)
**Refs:** #760 (item 2 only; item 1 is separate work and item 3 needs no action)

## Literal acceptance for item 2 (owner decision on #760)

"Proceed. Share a route-search memo across the extra passes. The gate is
byte-identical public output (a no-behaviour-change proof, per #575). Report the
slide-16 and 02 render times before and after."

Working acceptance: the extra rehearsal passes reuse identical route searches;
every committed Scene and SVG is byte-identical; the render times before and
after are reported honestly.

## Slices

| Slice | Content | Files | Publication |
| --- | --- | --- | --- |
| I760-2a | Profile, design, this plan | the two docs | docs PR, merged first |
| I760-2b | Route-search memo owned by the obstacle index; equivalence test and mutation check; timings | `src/chrona/presentation/layout/obstacles.py`, `src/chrona/presentation/layout/routing.py`, `tests/unit/chrona/presentation/layout/test_route_memo_equivalence.py`, this plan's evidence section | code PR |

## I760-2b work items

1. `_RouteMemo` (private, in `obstacles.py`): value-keyed result dict with
   `ROUTE_MEMO_LIMIT`, and a bounded interning dict for selection contents.
2. `SurfaceObstacleIndex`: owns a `_RouteMemo`; `copy()` shares it; a selection
   content id is computed lazily per `_PreparedSelection`.
3. `route_orthogonal`: when given an index, build the key, return a hit
   (re-raising a stored `RouteSearchFailure`), otherwise search and store;
   invalid `port_ids` and non-`RouteSearchFailure` errors bypass the memo.
   Signature and the search body are unchanged.
4. Equivalence test and mutation check per the design section 7.

## Gates for I760-2b

* Equivalence test passes; each mutation of the key fails it and is restored.
* `python -m tools.derived_evidence --check` and
  `python -m tools.regenerate_public_examples --check` pass with no derived
  change. If any committed Scene or SVG changes: stop, report the primitive and
  the cause, do not regenerate or merge.
* Focused routing, lane, composer and surface wiring tests;
  `tests/unit/chrona/presentation`.
* Before and after timing of slides 16 and 02 (minimum of three, wall and CPU,
  load stated).
* The PR notes that the source edit shifts line numbers in the diagnostic
  inventory, which CI's derived-sync regenerates; the PR edits no derived doc.

## Evidence

Baseline: see the design document section 1 (base `8ed48964`, host load average
170 to 220): slide 02 3.93 s wall / 1.59 s CPU; slide 16 46.7 s wall / 18.3 s CPU.
After (I760-2b, same commands, minimum of three back to back; host load average 143 to 153, lower
than the 170 to 220 of the baseline, so wall time flatters the change and CPU is the steadier figure):

| Slide | Wall before / after | CPU before / after | CPU speedup |
| --- | --- | --- | --- |
| `02-programme-board` | 3.93 s / 3.10 s | 1.59 s / 1.39 s | 1.14x |
| `16-gallery-editorial-lanes` | 46.7 s / 25.8 s | 18.3 s / 11.5 s | 1.60x |

Slide 16 meets the 1.5x expectation; the remaining cost is rehearsals 1 and 2 (about 6.6 s and 4.3 s
CPU of route search), which share no search because their placed member names differ. Byte identity:
all 29 public slides regenerate unchanged; only the diagnostic inventory's line numbers shift.
