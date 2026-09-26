# Design Correction — Lane Rows: Dependency Route Suppression at Mark Egress (#467)

**Corrects:** the [selected design](issue-467-collision-aware-lane-rows-design-2026-09-26.md)'s closure order and the [phase-and-version correction](issue-467-lane-rows-phase-and-version-correction-2026-09-27.md), which fixed lane names as phase-1 required text but did not evaluate the effect of that phase order on dependency routes.
**Evidence:** measured on the committed HALCYON `02-programme-board` lanes migration ([L3 slice 1](../reviews/current/issue-467-lane-rows-phase-correction-architecture-review-2026-09-27.md)); `11-overlay-briefing` and `12-glyph-gates` reuse the same View and reproduce identical counts.
**Authority requested:** the [#466 route-priority correction](issue-466-general-placement-route-priority-correction-2026-09-26.md) and the phase-correction architecture review both flagged this as an anticipated risk; this document measures it and proposes the fix for review before further product code.

## 1. Measured baseline

`02-programme-board`, `11-overlay-briefing` and `12-glyph-gates` each select 24 semantic relations. On all three, **17 of 24 are suppressed** (`W_LAYOUT_RELATION_SUPPRESSED`); the same 17 relation IDs, identical, on every slide, because they share one View and the suppression is a property of the shared Layout geometry, not of theme or context.

I instrumented the relation-routing loop in `layout/surface_composer.py` (not committed; reverted after measurement) to classify, for every one of the up to 16 source/target port-pair combinations tried per relation, which of three checks first rejected it:

- **`egress-collision`**: the connector's very first corridor segment, leaving its endpoint mark, collides with an obstacle before a route search even starts (`SurfaceObstacleIndex.egress_collisions`).
- **`no-route-found`**: `place_relation_route` raises inside the bounded search region — no orthogonal path exists there under the current obstacles.
- **`quality-rejected`**: a path exists but exceeds the declared bend/detour limits.

| Relation | Dominant cause(s) (of 16 pairs tried) |
| --- | --- |
| structure-avionics | 15 egress-collision, 1 no-route-found |
| eps-bustest | 13 egress-collision, 3 no-route-found |
| avionics-bustest | 15 egress-collision, 1 no-route-found |
| avionics-cdr | 12 egress-collision, 4 no-route-found |
| optics-detector | 15 egress-collision, 1 no-route-found |
| detector-tvac | 12 egress-collision, 4 no-route-found |
| bustest-integration | 15 egress-collision, 1 no-route-found |
| delivery-integration | 12 egress-collision, 4 no-route-found |
| integration-vibration | 15 egress-collision, 1 no-route-found |
| vibration-tvac | 16 egress-collision |
| tvac-emc | 15 egress-collision, 1 no-route-found |
| emc-psr | 12 egress-collision, 4 no-route-found |
| station-comms | 6 egress-collision, 10 quality-rejected |
| psr-shipment | 8 egress-collision, 8 no-route-found |
| shipment-campaign | 15 egress-collision, 1 no-route-found |
| frr-launch | 13 no-route-found, 3 quality-rejected |
| launch-leop | 12 quality-rejected, 4 no-route-found |

`egress-collision` dominates 14 of 17 relations. Cross-referencing each suppressed relation's two endpoint items against their accepted lane-label ladder level shows the pattern is **not** "a same-level `end`/`start` label sits on the corridor": most endpoints in this table used `label-row-1`/`label-row-2` (above the mark), not `end`/`start`. The real mechanism is that `connector_egress_candidates` always offers `above`/`below` corridors alongside `end`/`start`, and an `above`/`below` corridor's exposed point sits at the mark's own top/bottom edge — which is exactly where that same item's own required label rows are stacked (#467's lane ladder reserves label rows directly above the mark). A relation's connector therefore very often collides with **its own endpoint's own required name** before it ever reaches a genuinely shared obstacle.

## 2. Rejected option: exempt required labels from routing generally

As an upper-bound experiment, I patched the route search's obstacle classes to exempt every lane member-label from both `egress_collisions` and the full grid search (`SurfaceObstacleIndex.collisions`), scoped narrowly to the exact `("mark", "text", "label-visual")` class signature the relation loop uses (so ordinary label-vs-label placement was unaffected). Result: **0 of 24 suppressed** — every relation routes.

This is rejected as the fix. It exempts *every* label from *every* route, not just an endpoint's own name, so a route can and does cross a completely unrelated item's name — an unreviewed, silent visual defect (a line drawn through readable text) traded for a clean diagnostic count. It also contradicts the #466 route-priority correction's own language ("later labels must still avoid accepted route strokes," read symmetrically: routes must avoid accepted required text). I record the number only to show that **labels, not inherent mark geometry, are the practical ceiling** on this slide — the ≤12-lane bound is not the limiting factor.

## 3. Proposed fix: mark-egress clearance (own-endpoint exemption)

Scoped experiment: exempt only the *two endpoint items' own* required label (and its footprint obstacle) from a given relation's egress and route-search obstacle checks — the same principle the design already uses for the mark itself ("Ports carry clearance but do not block their own host"). Concretely: extend the existing per-relation host exemption (currently only the endpoint's *mark* obstacle) to also name that endpoint's own `member-label:<instance>` obstacle, for this relation's search only. Every other item's name remains a real obstacle.

Result: **9 of 24 suppressed** (down from 17; 8 relations now route): `structure-avionics`, `eps-bustest`, `optics-detector`, `integration-vibration`, `station-comms`, `shipment-campaign`, `frr-launch`, `launch-leop`.

Remaining 9 (`avionics-bustest`, `avionics-cdr`, `detector-tvac`, `bustest-integration`, `delivery-integration`, `vibration-tvac`, `tvac-emc`, `emc-psr`, `psr-shipment`) keep failing mostly on `no-route-found`/residual `egress-collision`: their corridors must still cross a *different* item's name along a multi-row path, which this narrow exemption correctly leaves as a real obstacle.

This stays inside the published phase contract: required text is still placed first and is still a real obstacle to every route except the one connector that belongs to that same name. It is implemented as an additive exemption-set parameter next to the existing host/port exemptions in `SurfaceObstacleIndex.egress_collisions`/`collisions` and `route_orthogonal`'s obstacle handling, not a new obstacle class or a phase reordering.

## 4. Rejected (as tested) option: a uniform routing gutter

Tested: add a flat 12px to each lane row's required block extent (independent of `mark_row_height`, so labels and marks keep their position and a purely empty band appears at the bottom of every row). Result: **20 of 24 suppressed** — *worse* than baseline. A blanket gutter does not address egress-collision (the label is still immediately adjacent to the mark; empty space below the row does not help a corridor leaving from the mark's top edge into its own label), and it makes every long-distance relation's bounded search region taller, which increased detour ratios and grid-search misses for `no-route-found`/`quality-rejected` cases (`frr-launch`, `launch-leop`, `psr-shipment` among others).

A gutter is not rejected in principle — a *targeted* dedicated routing lane between groups, decoupled from per-row height, could still help the remaining 9 — but a naive uniform version measured net negative and needs its own design and measurement before being proposed. I am not proposing one in this correction.

## 5. Recommendation

Adopt the mark-egress clearance exemption (§3) as the #467 L3/L4 fix: it is additive, scoped, measured, stays inside the published phase contract, and halves suppression on the hardest committed fixture with no visual-quality regression. The remaining 9 suppressions on `02`/`11`/`12` are recorded here with their measured cause and are accepted as `narrowed` for L4, each cited individually with this document, unless a follow-up routing-gutter design (§4) is separately proposed, measured and accepted.

## 6. Acceptance target

- No relation on `02` (or `11`/`12`) is suppressed for `egress-collision` against its *own* endpoint's own required name once §3 lands.
- Every relation still suppressed after §3 is listed in the L4 acceptance review with its measured cause (`no-route-found` or residual cross-item `egress-collision`), citing this document.
- No change to lane count, chain narrowing, or any other #467 literal acceptance row.
