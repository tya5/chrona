# Architecture Review — Collision-Aware Lane Rows (#467)

**Reviewed:** [selected design](../../design/issue-467-collision-aware-lane-rows-design-2026-09-26.md) and [design plan](../../planning/active/issue-467-lane-packing-design-plan-2026-09-26.md) against current code, Specifications 06, 08, 33, 38, 44 and 50, #466's obstacle-only design, #449 visible overflow, #468 host growth, #440 point folding and #434 fill distribution.

## Consistency findings

1. Specification 38 §3 and its boundary table still assign subtrack geometry and label failure to Scene. This conflicts with Specifications 08/33/50 and the current Layout composer. Specification 38 is corrected with this review; Scene is a placement projection, not a collision owner.
2. Row membership is a View fact only for authored `explicit` rows. Automatically selected Review Items and group keys remain View facts, but `lanes` row membership is a Layout decision. Encoding a lane ordinal in a source item or View projection would make identities unstable and leak geometry upstream; the design prohibits it.
3. The existing per-item `tableColumns` grammar has a single `tableSubject` per row. Applying it to a packed lane would silently misattribute phase/date/delta facts. A versioned `laneTable` summary grammar, with item facts moved explicitly to plot labels or intentionally removed, is therefore required. `automatic` and old explicit tables remain unchanged.
4. Measured name/delta footprints must constrain packing before final block coordinates are assigned. Layout can measure in a lane-local frame, allocate natural row height, translate accepted geometry once, then route relations. This matches #466's monotone obstacle phases and #468's content-coherent host growth. A Scene repair pass or mark-only first-fit is rejected.
5. The issue's explicit-row request conflicts with exact old-output preservation if applied unconditionally. A v0.23 `trackAllocation: collision` opt-in for `explicit` rows gives collision packing without changing v0.22 authored compositions. `track: stacked` still requests a dedicated subtrack; `shared` admits collision-based sharing. The v0.23 schema and tests must enforce this distinction.
6. `hierarchy` grouping carries parent-row nesting, not just group segregation. Packing it into group lanes without a hierarchy-specific table and ancestry rule would discard meaning. Excluding it from this version keeps 06 automatic; the third lane slide can be another non-hierarchy View. This is an intentional admitted-domain limit, not silent fallback.
7. Bounded lane-label stagger uses the shared obstacle index but is not #466's View-authored annotation candidate grammar. It is safe to implement after #466's obstacle-only prerequisite; #466 itself remains open until its separate candidate/search/tail acceptance is complete.
8. Theme roles, Context closure, Project dependency semantics and adapter geometry boundaries remain unchanged. `fill` and as-of/annotation avoidance are inherited Layout rules. No compatibility shim should reinterpret a v0.22 `automatic` View as `lanes`.

## Decision and implementation guard

The selected design is accepted for implementation planning, conditional on a focused feasibility fixture proving that the measured-lane algorithm can meet HALCYON 02's at-most-twelve-lane bound and chain rule. This is a design-validation gate, not permission to weaken either criterion. If that fixture fails, stop and publish a design correction and amended implementation plan before product code is adapted around it.

The #466 obstacle-only stage must be published and verified before #467's collision code is accepted. The later #466 candidate/tail design is deliberately not treated as complete. A new implementation discovery that changes View schema, lane identity, label guarantee, table meaning or layer ownership returns to design and whole-architecture review first.
