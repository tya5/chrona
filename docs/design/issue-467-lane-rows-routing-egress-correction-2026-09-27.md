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

## 5. Addendum — §3 fails the visual-integrity test; not shipped

Review of this correction (conditionally approved pending two conditions) asked for the exemption's scope to cover only the egress stub (mark port to the edge of the label it clears), never the routed segments beyond it, and for an integration test asserting that no rendered relation path segment intersects any member-label text box, own or other, with a small tolerance.

**Scoping the exemption to the egress stub only** (`egress_collisions`, not the full-route `collisions` search): re-measured at **17 of 24 suppressed — identical to baseline, zero relations fixed**. The stub alone is too short to matter: an item's own label sits directly against the mark's own top edge, so clearing the initial hop still leaves the full orthogonal search blocked by the same obstacle immediately afterward.

**Alternative inside the same principle** (drop the `above`/`below` egress candidate entirely for an endpoint whose own label occupies a stagger row, so the connector only ever offers to leave by `end`/`start`): re-measured at **18 of 24 suppressed — worse than baseline** (removing a candidate side forces fallback pairs with worse detour/quality outcomes, newly suppressing `campaign-frr`, which had routed at baseline).

**The full exemption (§3, both egress and the whole route search)** was then checked against the requested test (`tests/integration/test_materialize_example.py::test_lane_relation_routes_never_cross_a_required_lane_label`, added in this correction): it **fails**. E.g. `relation:pdr-structure` — a relation that already routed at baseline — now runs its full path straight through `member-label:lane:bus:pdr:pdr` (`pdr`'s own name, one of its own endpoints), because the exemption makes the direct path through that box legal for that endpoint. This is exactly the defect flagged in review: an endpoint's own name struck through is the same reading problem as a bystander's.

**Conclusion: no variant of the mark-egress clearance idea is shipped.** §3's "Result: 9 of 24" and §5 (original)'s recommendation are superseded by this addendum. The test above is kept as a permanent regression guard (it passes at baseline, since a suppressed relation draws no path and a routed one inherently avoided every obstacle already) and must keep passing if any future routing change is proposed for lanes.

**Disposition:** baseline stands — **17 of 24 suppressed** on `02`, `11` and `12`, cited individually by measured cause (§1) in the L4 acceptance review as `narrowed`. A follow-up issue is warranted for a properly designed, separately measured fix (e.g. a targeted inter-group routing gutter, §4, or a route search that actively routes *around* its own label rather than through it) — filed by the issue owner, out of scope for #467 L3/L4.

## 6. Acceptance target (superseded by §5 addendum)

- ~~No relation on `02` (or `11`/`12`) is suppressed for `egress-collision` against its *own* endpoint's own required name once §3 lands.~~ Not adopted; see §5.
- Every relation suppressed at baseline is listed in the L4 acceptance review with its measured cause (§1), citing this document.
- No change to lane count, chain narrowing, or any other #467 literal acceptance row.
