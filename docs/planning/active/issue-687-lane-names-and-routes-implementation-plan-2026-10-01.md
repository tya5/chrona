# Implementation Plan — Lane Member Names Placed Before Routes (#687)

Design: [design](../../design/issue-687-lane-names-and-routes-design-2026-10-01.md), with the findings of the
[architecture review](../../reviews/current/issue-687-lane-names-and-routes-architecture-review-2026-10-01.md).
Related: [#573 plan, slice I679-1](issue-573-label-behaviour-knobs-implementation-plan-2026-09-30.md) (the final rung), Spec 50 §3.2-§3.3, Spec 33 §8.3 (surface module ownership, #592).

## Baseline (main `2f0b83ef`)

- `surface_composer.compose_surface_layout` runs `place_label_phase(pre_route)` (as-of label and, in lane mode, every member name), then `compose_surface_routes`, then `place_label_phase(post_route)` and `place_relation_labels`, all on one `SurfaceObstacleIndex`. `tests/integration/test_surface_phase_wiring.py` pins that order, the one index object and its monotone growth.
- Four public relations are suppressed (`launch-leop` on `halcyon-1` slides `02-programme-board`, `11-overlay-briefing`, `12-glyph-gates`; `shipment-campaign` on `16-gallery-editorial-lanes`), each `quality-rejected`.
- Routing cost dominates a lane render with relations (15 s per pass on slide 16); member-name placement does not (about 0.05 s).
- The composer is 294 lines and must stay under 400; every `surface_*.py` module needs a row in the Spec 33 §8.3 table, a reachability entry and a docstring starting `Owns ...; reads ...`.

## Literal acceptance (issue rows)

1. A synthetic fixture (no `examples/` input) reproduces a name blocking a route and showing `W_LAYOUT_RELATION_SUPPRESSED`; the fixture fails today if the order is changed so that `end` wins.
2. The design states the order and its reason, and Spec 50 says so.
3. If behaviour changes, corpus evidence is regenerated and each changed slide is reviewed against the general rule and the design targets.

## Slice I687-1: corridor plan for relations that names alone would lose (code PR)

Owned files: `src/chrona/presentation/layout/surface_lane_route_plan.py` (new), `obstacles.py` (`SurfaceObstacleIndex.copy`, `ROUTE_RESERVE_CLASS`), `routing.py` (`ROUTE_GRID_OFFSET`, same value as today's default), `surface_member_labels.py` (one class added to the classes a non-rule label avoids), `surface_composer.py` (call the planner, extend the index with its corridors, before the name batch), Spec 50 §3.3 and Spec 33 §8.3 (module row), tests below.

Behavior:

1. `plan_lane_route_reservations(LaneRoutePlanContext) -> LaneRoutePlan` returns an empty plan unless the projection has lanes, the Surface has relations and a member name is requested.
2. It rehearses the name batch and the route phase on `obstacles.copy()`. Lost relations are those suppressed or completed as a visible direct fallback. None lost: empty plan.
3. It routes on a private copy of the pre-name index (same router, no names) and keeps the relations that now have a route. None: empty plan.
4. Corridors are the segments of those routes, as `route-reserve` obstacles of width `stroke + 2 * ROUTE_GRID_OFFSET`, identified `route-reserve:<relation id>:segment:<n>`.
5. It rehearses again with the corridors and keeps them only if the relations lost are a strict subset of those lost before and no name is suppressed that was not suppressed before. Otherwise an empty plan.
6. The composer extends the one index with the plan's corridors and places names, routes, post-route labels and relation labels exactly as before. Rehearsals use copies and return no placement.

Tests (all synthetic, decided from data, no platform-dependent ordering):

- The six-span fixture (design) loses `r0` with the plan disabled (`W_LAYOUT_RELATION_SUPPRESSED`, `I_LAYOUT_LANE_ROUTE_CAUSE` with primary cause `quality-rejected` and no `egress-collision`) and draws it with the plan; every name is shown, each within its host and 2 em reach, and the route clears every name and mark.
- Mutation check: replace the planner with an empty plan on a worktree copy, the fixture fails; restore.
- A name with no conflict keeps its position exactly (rendered with the plan disabled and enabled on a fixture whose relation is never lost).
- The seven-span fixture keeps today's result (relation lost, all names shown) because the only repair suppresses a shown name; the guard is what is tested.
- Unit: a project without relations or without lanes returns the empty plan and runs no rehearsal; the corridor class is not selected by the route search or the relation labels; `SurfaceObstacleIndex.copy` is independent of the original.
- Existing: the #592 ownership and wiring tests, the surface phase and synthetic-surface tests, `tests/unit/chrona/presentation`, `tests/unit/tools`, conformance, `tools/check_import_direction.py`.

Evidence (local; the PR carries source only): regenerate with `python -m tools.derived_evidence` and `python -m tools.regenerate_public_examples --write`, review the diff of every changed Scene and SVG, list each changed slide and primitive class and explain it against the rule and the design targets. Expected: `halcyon-1` slides `02`, `11`, `12` only (a drawn `launch-leop`, four moved names, one name shown that was suppressed, three rerouted relations; on `11` one annotation box moved). Anything else, or a lost relation, annotation or name, is a stop condition and is reported instead of merged.

PR body: sources only; derived docs regenerate in CI's derived-sync and a source edit shifts diagnostic line numbers.

## Open decisions for the owner (not taken here)

- Slide 16 keeps `shipment-campaign` suppressed: drawing it costs three names that are shown today. Whether a route outranks names in that case (option E2) is the owner's call.
- A route-search memo shared by the rehearsals would cut the cost on slide 16 from three route passes to one extra; follow-up, not in this slice.

## Publication

Docs PR (this plan, the design and the review) first; I687-1 code PR. Every commit and PR: `Refs #687`, no closing keywords, PR titles end with the slice id. The acceptance review and issue closure are separate, later work.
