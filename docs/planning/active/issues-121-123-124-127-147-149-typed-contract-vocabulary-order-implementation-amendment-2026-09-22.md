# Typed Contract Vocabulary Order — Implementation Amendment

**Amends:**
`issues-121-123-124-127-147-149-implementation-plan-2026-09-22.md`

**Design authority:**
`docs/reviews/current/issues-121-123-124-127-147-149-typed-contract-vocabulary-order-design-correction-2026-09-22.md`

## Revised sequence

P3 and P4 remain ordered as published.  Insert P4.5 immediately after P4 and
before P5/P6 implementation or #147 closure.  P3/P4 must continue to use the
single completed resource parsing seam; they must not introduce a second
parser, temporary generic-document accessor, or compatibility record layer.

## P4.5 — #147 typed presentation vocabulary closure

Replace each remaining contract-owned, closed-schema adapter mapping with a
frozen named record after the P4 View/WBS vocabulary is final.  The slice
introduces `TableColumn`, `LegendEntry`, `SummaryPanel`, and the named
row/group/visibility records required by the final schemas.  It adds
field-level schema-to-record completeness fixtures, migrates their consumers,
and leaves a frozen mapping only for explicitly schema-declared open extension
payloads.

**Constraints:** The change is representation-only.  It must not change Project
scheduling, WBS selection/order/depth, Layout geometry, Scene projection, or
renderer/materializer policy.  The existing parser remains the only boundary
that decodes raw YAML.

**Acceptance:** every closed schema field is represented by a named immutable
record field; no raw YAML mapping reaches the render use case, projection,
content, Layout, Scene, or renderer; mutation-after-decode isolation and
validation-before-construction remain proven; public materializer bytes remain
unchanged; focused tests, full suite, conformance/package/reachability checks,
and macOS/Ubuntu CI pass.

## Closure and release dependencies

#147 is not closed by the P2 foundation.  It closes only when P4.5 is merged
and its acceptance evidence is published.  P7 follows P3, P4, P4.5, P5, and
P6, and retains the final cross-issue inventory and release review gate.
