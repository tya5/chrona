# Design Plan Amendment — S2b completed-geometry closure reconciliation (#467, #494)

**Public base:** `980a8e700ec0a7fda0474ee799dc040202d217a7`. **Amends:** [S2 facet design plan](issue-467-b1b2-facet-count-asof-design-plan-2026-09-27.md), [S2 mapper implementation plan](issue-467-b1b2-facet-count-asof-implementation-plan-amendment-2026-09-27.md), and the [rule-based L3 plan](issue-467-494-rule-based-lane-acceptance-implementation-plan-2026-09-27.md). S2b remains uncommitted in an isolated worktree after two independent architecture audits found that copying completed automatic-row placements as lane-local geometry is not a closed contract. Published S2a port/icon types, Scene lane identity carrier, and shared label-visual measurement are independently verified slices, not evidence that S2b/B2 is complete.

## Baseline and questions to settle before code

1. **Coordinate frame.** The allocator requires lane-local mark-band geometry, while the draft mapper copies absolute automatic-row marks, ports and footprints. Decide a shared Layout mark-geometry function parameterized by an explicit `MarkBandFrame`, including planned/snapshot/Actual/open/point/progress/icon variants, or a rigorously equivalent typed transform. Preserve the exact automatic formulas/Decimal order, and ensure B2 applies one final lane-band translation only.
2. **Closed source/projection identity.** Resolve attached host by canonical object and exact Review projection instance, not an `object_id`/`item_id` mixed key. Reject ambiguous/missing hosts and missing expected comparison/Actual/point placements instead of silently omitting them. Preserve item/source/row identities through allocation and B2.
3. **Intentional overlay.** Map selected `ReviewItem.track`/shared-subtrack and declared host/progress semantics; do not mark every comparison-source pair as exempt. Stack-only visuals remain collision obstacles. Retain icon emission metadata when copying facets.
4. **B2 authority.** The immutable preflight plan must retain exact candidate/facet and required-label closure, selected `as_of`, measurement/Theme/scale identity, so B2 does not remap or recompute. State cutoff mismatch and seed/final inline failure behavior.
5. **Projection payload.** Complete per-glyph-part paint mode/color, icon group metadata, title/delta content and `labelVisual` bundles. Make an exhaustive emitted-primitive allowlist; unknown needed facts fail closed. Preserve progress clip/paint constraints and folded-point domain choice.

The selected design must review these choices against the whole architecture: Project/Schedule/Actual semantics; View v0.27 and attachments; Theme, icon catalog and font metrics; Layout preflight/table/group/row solve; Scene v0.6 completed primitive/paint/provenance contract; adapters; Specs 38/46/50 and #466/#494 route phase; #498 preset defaults. Do not encode a numeric lane-count target or reintroduce a forced third label row.

## Design and publication slices

Publish this plan first. Then publish one consolidated design correction, normative Spec 38/46/50 changes as needed, and a whole-architecture review. Then publish an implementation-plan amendment with independent shared-mark extraction, typed payload/identity/overlay closure, mapper/preflight, B2 one-plan projection and generated-evidence gates. Only approved code slices resume. Focused tests include automatic planned/snapshot/Actual/point byte-characterization, lane-local geometry and ports, attached identities, track/overlay matrix, glyph/icon/progress payload, as-of matching, missing-geometry failures, one-plan exact identity, and direct hidden Scene rule proof. Batch 28 public materializers and SVG/Scene diffs once per material unit; CI supplies full matrix at release.

## Literal issue acceptance retained

### #467

1. A lane row mode exists. On `02-programme-board` the chain `structure → avionics → bus-test` is on one lane, and the lane count is **justified by the rule, not by a target number**. Both checks read the Scene footprints (marks, comparison marks, names, deltas, icons):
   - **No redundant lane.** For every pair of lanes in the same group, moving all items of one into the other would make two footprints collide. The only exception is a pair kept apart by the chain rule, and those pairs are listed.
   - **Lower bound reported.** For each group, report the maximum number of footprints that overlap at one date, next to its lane count, and attribute any difference. The lower bound is reported and explained; it is not a target.
   *(Amended 2026-09-27 twice: "at most 12" and then "at most 14" were arbitrary numbers and are withdrawn; see the comments.)*
2. Every packed task and milestone has a visible name on the slide; no `W_LAYOUT_LABEL_SUPPRESSED` for a packed item on any committed slide.
3. Lane assignment is deterministic, and a test shows that one inserted item does not reorder unrelated lanes.
4. Deltas remain visible for packed items that have them.
5. New Views and the packaged presets default to lanes; `automatic` still renders exactly as today.
6. At least three committed slides use lanes (for example `01`, `02` and `06`), and their evidence is reproducible.

### #494

1. On `02-programme-board` (lanes), no relation is suppressed for `egress-collision`, and every remaining suppression is listed with a measured cause.
2. `test_lane_relation_routes_never_cross_a_required_lane_label` still passes on 02, 11 and 12: no route crosses any lane or member label.
3. Lane count and lane membership on 02 are unchanged, or any change is attributed.
