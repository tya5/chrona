# #466 C3 routed-tail design plan

**Base:** published `main` `56f65735` (#505 merged). **Predecessors:**
[candidate design](../../design/issue-466-candidate-placement-design-2026-09-26.md),
[connector topology design](../../design/issue-466-annotation-connector-topology-correction-2026-09-26.md),
and the [current work record](issue-466-annotation-placement-work-record-2026-09-28.md).
This is a design gate, not permission to implement.

## Published facts and unaccepted trial

The current public 02 View uses eight lanes and has no three-note C3 resource
declarations. In an unpublished trial with only those declarations and the
balloon Theme binding, 15 focused candidate tests passed, but actual
Scene/SVG/PNG failed issue #466 criterion 3. `window-note` fit directly in 6
trials; `tvac-note` and `station-note` exhausted their complete 348-position
12em lattice and visibly overflowed across marks, labels, and dependencies.
A bounded 18em probe also failed (387 and 301 positions). Both notes have
many collision-free box positions below the packed rows, but no direct
triangular tail from the specified anchor clears the intervening geometry.
The as-of side, obstacle classes, 1024-position declaration, and anchor facts
were not weakened. These are diagnostic local artifacts, not published C3
acceptance.

## Design questions and required review

Determine whether a strict, bounded route can connect each named anchor to
a free in-plot balloon without crossing any declared obstacle or the as-of
barrier. A route may be considered only as a **tail connector** with a Theme
balloon outline, never as a rail fallback, unreported leader substitution,
perimeter detour, or missing note. Reuse the existing Layout-owned connector
egress/topology machinery where its bounded local corridor and endpoint
exemptions satisfy this contract. Establish a concrete route for each failed
note before selecting the correction; otherwise report the literal fixture
infeasible under current constraints and seek an issue-owner disposition.

If feasible, specify direct-versus-routed ordering, View syntax/version and
migration, box/tail/route geometry and identity, endpoint and as-of rules,
bounded search counts and diagnostics, Theme paint role, Scene projection,
SVG/PNG parity, and exact fallback behavior. Review against Specs 06/07/08,
33/44/50, the direct-tail design, #449 visible fallback, and C4 contrast.
Project content and View source consumption must remain unchanged. Layout
must still commit box and connector atomically from the one obstacle index.

## Design slices and evidence

1. Reproduce the 8-lane failure and prove whether strict routed-tail paths
   exist for `tvac-note` and `station-note` with the exact current obstacles,
   box dimensions, as-of side, and connector-quality bounds.
2. Publish a minimal design correction, normative specification changes and
   whole-architecture review. Do not change product code before that review.
3. Amend the C3 implementation plan with affected files, version/resource
   migration, focused geometry/Scene tests, public materializers and a
   separate publication boundary. C4 remains after accepted C3.

Acceptance evidence remains every literal #466 row in the [work
record](issue-466-annotation-placement-work-record-2026-09-28.md), especially
all three actual 02 balloons, no forbidden intersections or as-of crossing,
one crowded plot-to-rail fallback, bounded decisions, unchanged unrelated
materializers, rendered SVG/PNG, and the final CI matrix. A green unit test
or a box-only fit cannot accept C3.
