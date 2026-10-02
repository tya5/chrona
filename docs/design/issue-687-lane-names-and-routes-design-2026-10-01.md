# Design — Lane Member Names Placed Before Routes (#687)

**Plan:** [implementation plan](../archive/planning/issue-687-lane-names-and-routes-implementation-plan-2026-10-01.md); **review:** [architecture review](../archive/reviews/issue-687-lane-names-and-routes-architecture-review-2026-10-01.md), whose findings are part of this design.

## Question

In lane mode the member names (Spec 50 §3.2) are placed before the dependency routes (Spec 50 §3.3, the phase order of #592: names, routes, post-route labels, relation labels, annotations). A name is an obstacle to every route, so name placement can be the reason a dependency line is suppressed. The design targets (PR #461 and the HALCYON target mock) draw every dependency. Should the composition reserve what a route needs before it places a name, rank `above`/`below` over `end`, place routes first, or leave the order alone? (#679 raised it: a first variant of that slice lost three routes, `bustest-integration` on `02-programme-board` and `12-glyph-gates`, `structure-avionics` on `16-gallery-editorial-lanes`, and was narrowed to a final rung.)

## What was measured first

All numbers are on main `2f0b83ef`, with `executive-light` for synthetic fixtures and the committed HALCYON views for public slides.

1. **The conflict exists on public slides today.** Four relations are suppressed on four committed slides: `launch-leop` on `02-programme-board`, `11-overlay-briefing` and `12-glyph-gates`, and `shipment-campaign` on `16-gallery-editorial-lanes`. Every one is `quality-rejected` (16 of 16 port pairs, plus 4 `no-route-found` on slide 16). Names are the cause: with the member names placed after the routes (option C below) all four relations are drawn.
2. **The cause is not an end-side name sitting on the exit port.** None of the measured suppressions (the four public relations and synthetic seeds 459 and 516) has an `egress-collision` attempt. The routes are rejected for 5 to 7 bends against a maximum of 4, because names in stacked lane rows form a wall across the channel between the source's end and the target's start. A name beside the port is one stone of that wall, not the blocker. Reserving only the port corridor (option A) therefore cannot fix it.
3. **The conflict appears in small synthetic projects.** Random lane projects (two to four lanes, two to four spans per lane, up to six dependencies): of 600 seeds, two lose a relation with names present that is drawn with the names removed (seeds 459 and 516, both `quality-rejected`); of another 1,200, one changes under option E (seed 872). The reductions of seeds 516 and 872 (seven and six spans, one relation each) are the two fixtures of this design. In the six-span fixture (`l1-t0` end to `l3-t1` start) the name of `l0-t0` sits at its end in the vertical channel and the name of `l1-t0` sits at the exit port; moving the first to its `start` side draws the route and keeps all six names. In the seven-span fixture the only ways to draw the route suppress a name that is shown today.

## Options

Each option was prototyped on a worktree copy and the whole public corpus regenerated; Scene primitives were diffed by id.

| Option | Phase order / ranking | Public slides changed (measured) | Routes | Names | Verdict |
|---|---|---|---|---|---|
| A. Reserve the port corridor before names (12 px keep-clear at each relation port) | names see a reserved box; routes unchanged | five: `02`, `03`, `11`, `12`, `16` (moved names, rerouted relations) | `launch-leop` stays lost on three slides; on `16` `shipment-campaign` is drawn but `station-comms` is newly lost | 1 name suppressed on each of `02`, `11`, `12`; 14 on `16` | Rejected: loses a route and drops names, fixes nothing it was meant to |
| B. Rank `above`/`below` over `end` when `end` meets a route exit | ladder order only | none (no lane view declares `above`/`below`; presets declare `end`, `start`) | unchanged | unchanged | No effect: with `above`/`below` first in the synthetic ladder the route is still lost; with only `above`/`below` all names are suppressed (the route is drawn only because no name exists) |
| C. Routes first, names second, names yield | the pre-route name batch moves after routes | five: `02`, `03`, `11`, `12`, `16` | all four lost relations drawn | 8, 5, 6, 8 and 13 names suppressed, 40 names that are shown today | Rejected: names are required lane content; trades 40 names for 4 routes |
| D. Do nothing; keep the final-rung-only rule | none | none | four relations stay lost | unchanged | The structural order stays and four public dependencies stay missing |
| E. Plan route corridors for relations that names alone would lose (recommended) | one planning step before the name batch; the name, route and post-route phases keep their order and one index | three: `02`, `11`, `12` | `launch-leop` drawn on all three; nothing lost; `16` unchanged (still lost) | none suppressed; one name per slide that was suppressed is now shown (`frr` on `02` and `12`, `launch` on `11`) | Recommended |

E with the name guard removed (E2: the route always outranks names) draws all four relations and on `16` suppresses three names that are shown today (`frr`, `launch`, `leop`); it is the owner's decision whether that trade is wanted and it is not made here.

## Decision

**E: reserve a corridor only for a relation that the names alone would lose, and let the names yield only to that corridor.** The rule is general (any lane project) and has no corpus input.

1. **Order.** The phase order is unchanged: required pre-route text and names, then routes, then post-route labels and relation labels (Spec 50 §3.3). One new step runs before the name batch. It rehearses today's name and route phases on a private copy of the obstacle index. If no relation is suppressed or completed only as a visible direct fallback, the step returns nothing and the composition is exactly today's.
2. **Reservation.** For each relation lost in the rehearsal, the step routes it again on a private copy of the pre-name index (the same router and limits, with no member name present). If a route exists, its segments become a corridor of obstacle class `route-reserve`, as wide as the relation stroke plus the router's grid offset on each side (`ROUTE_GRID_OFFSET`, 2 px). Member-name placement lists `route-reserve` among the classes it avoids; routes, relation labels and annotations do not select it, so it never constrains anything else.
3. **Guard.** The step rehearses the names and routes again with the corridors. It keeps them only if the relations lost afterwards are a strict subset of the relations lost before, and no name is suppressed that is shown without them. Otherwise it returns nothing and the result is today's, so the step can never make a route or a name worse than the current order, by construction and by test.
4. **Real placement.** The composer adds the corridors to the one shared `SurfaceObstacleIndex` before the name batch, then runs the name, route and relation-label phases on that index exactly as now. The rehearsals use private copies of the index and return no placement; they are a planning value, not shared mutable state. The index stays monotone and the same object in every phase.
5. **Names move only through the existing ladder.** A name that yields takes the next legal candidate of its declared ladder with the same association and reach checks (host, 2 em), or is suppressed with the usual typed fact. The planner never places or moves a name itself.

## Why E

- It fixes the measured defect (three of four public relations, and the synthetic fixture) with the smallest behaviour change: three slides, no suppressed name, no lost relation.
- It is the only option whose acceptance is checked at run time. A and C change names and routes unconditionally, so a regression is found only by reviewing a corpus diff; E refuses a trade that costs a name or a relation by construction.
- It keeps the Spec 50 statement that names are required lane content and routes never cross them. The corridor is a hint for where a name may not stand, not permission for a route to cross a name.

## Determinism and tie-breaking

The rehearsals run the same deterministic placement and routing on copies, so the plan is a pure function of the closed Layout input. Reservation obstacles are identified `route-reserve:<relation id>:segment:<n>` and the index orders obstacles by identifier, so insertion order never matters. The only new arithmetic is `stroke + 2 * ROUTE_GRID_OFFSET`, a sum of two IEEE doubles with no reordering or fusing, identical on every platform. Name tie-breaking (side order, absolute block displacement, smaller block coordinate, stable identity) is unchanged; a corridor only removes candidates.

## Risk to the Scene acceptance checks

Association, host and the 2 em reach are enforced by the same candidate filter for every candidate, so a name that yields cannot be emitted outside them. The final rung of #679 is part of the same ladder and is unaffected. The `hostPlacementId` of a moved name is the host of the candidate that was chosen, as today. Scene schema, Scene builder and adapters do not change; only the Layout facts that follow from placement (`laneMembers`, `laneObstacles`, `fitWarnings`, the diagnostics) change on the three slides, and each is reviewed with the primitive diff.

## Cost

Only lane projects that have relations pay. Two extra route passes run when no relation is lost (one rehearsal) and up to three when one is (rehearsal, reference route, guarded rehearsal), because routing, not name placement, is the cost: name placement is about 0.05 s on `16`, routing 15 s per pass. Measured wall time per slide: `programme-board` 3.1 s to 4.5 s, `launch-campaign` 1.9 s to 2.4 s, `gallery-editorial-lanes` 22 s to 50-58 s. The long pole of the public regeneration grows by about 30 s. A route-search memo shared by the rehearsals is the follow-up if that matters; it is not in this slice.

## Stop conditions

Stop and report instead of merging if the regenerated corpus shows any of: a relation, annotation or dependency that is drawn today and is lost or degraded; a member name suppressed that is shown today; any changed primitive that the rule above does not explain (a primitive on a slide without lanes or without relations, a mark, a table cell, an axis label); a Windows-only or ordering difference in the new synthetic tests.

## Tests

Synthetic only (`tests/support/synthetic_review.py`, no `examples/`): the six-span fixture loses the relation today (`W_LAYOUT_RELATION_SUPPRESSED`, `I_LAYOUT_LANE_ROUTE_CAUSE` `quality-rejected`) and draws it with the plan, with every name still shown and every name within its host and reach; the seven-span fixture keeps today's result because the only repair would suppress a shown name; a name with no conflict keeps its position exactly (compared with the plan disabled); the mutation check disables the corridor and the fixture fails. Unit tests cover the planner returning nothing when nothing is lost, and the corridor class being invisible to routes.

## Boundaries

Layout placement only: one new surface module (`surface_lane_route_plan`, added to the Spec 33 §8.3 ownership table), a copy method on the obstacle index, one obstacle class, one routing constant, a one-line class addition in member-name placement. Spec 50 §3.3 states the order and the corridor. No schema, Theme, View, Scene or adapter change.
