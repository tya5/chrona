# Implementation Review — L3b B1b-1 Atomic Bundle Allocator (#467, #494)

**Status:** Accept the neutral allocator's atomic-bundle extension as the partial B1b-1 slice. All six #467 and three #494 literal acceptance criteria remain deferred. **Reviewed commit:** `9d5c0c72` (`feat(layout): extend lane allocator for atomic bundles`, including regenerated diagnostic inventory). **Base:** published `main` `4b6cfe63`. **Plan:** [B1b atomic-bundle publication amendment](../../planning/active/issue-467-l3b-atomic-bundle-publication-amendment-2026-09-27.md). **Design:** [atomic bundle and row translation correction](../../design/issue-467-l3b-candidate-footprint-correction-2026-09-27.md), [architecture review](issue-467-l3b-candidate-footprint-architecture-review-2026-09-27.md), and [Specification 38 §3.1](../../specification/38-review-row-composition.md).

This review covers only the direct Layout allocator seam. The projection-to-bundle mapper (B1b-2), content solve and one-plan realization (B2), route-cause integration (B3), and public lane activation and resource migration (L3c) remain separate deferred slices. The public `_project_review` lane guard remains in place.

## Implementation and evidence

The change extends `lane_allocation.py` with immutable `LaneMember` data, member-specific mark and label footprints, explicit pairwise mark-overlay identities, and per-member placements under one root candidate. The allocator checks all proposed member marks against accepted lane content, rejects undeclared internal mark collisions, then attempts the finite label ladder in deterministic bundle order on a trial obstacle index. It commits a bundle to one lane only after all members have placements; member identities are retained in the lane result. A terminal result retains visible-overflow placement for every member. Existing single-member candidates continue through the same path as a one-member bundle.

The focused Layout verification passed **37 tests**. The float/geometry check passed. Module reachability reported **97 reachable, 2 staged, 0 orphaned**. All **28 public materializers** passed their check with no generated Scene or SVG changes. These checks characterize the isolated kernel and automatic-mode output; they do not exercise projection mapping or rendered lane output.

[CI run 36301827524](https://github.com/tya5/chrona/actions/runs/36301827524) passed: Ubuntu, macOS and Windows conformance/full pytest/wheel-smoke, and newest-Python public-materializer reproduction all succeeded. The only generated change in the product commit was the intended diagnostic inventory update; no public Scene/SVG bytes changed.

## Literal issue acceptance

<!-- chrona:literal-acceptance/v1 -->

### Issue #467

- Source: [Issue #467](https://github.com/tya5/chrona/issues/467)
- Observed: 2026-09-27

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | A lane row mode exists. On `02-programme-board` the 26 items occupy at most 12 lanes, with the chain `structure → avionics → bus-test` on one lane. | deferred | [B1b-1 allocator](https://github.com/tya5/chrona/blob/f3688940/src/chrona/presentation/layout/lane_allocation.py) has no ReviewProjection mapper or composer integration; public lane rendering remains fail-closed. | [B1b-2/B2 plan](../../planning/active/issue-467-l3b-candidate-footprint-implementation-amendment-2026-09-27.md) |
| 2 | Every packed task and milestone has a visible name on the slide; no `W_LAYOUT_LABEL_SUPPRESSED` for a packed item on any committed slide. | deferred | [Focused allocator tests](https://github.com/tya5/chrona/blob/f3688940/tests/unit/chrona/presentation/layout/test_lane_allocation.py) exercise placements only; no lane-rendered committed slide is produced in this slice. | [B1b-2/B2 plan](../../planning/active/issue-467-l3b-candidate-footprint-implementation-amendment-2026-09-27.md) |
| 3 | Lane assignment is deterministic, and a test shows that one inserted item does not reorder unrelated lanes. | deferred | [The kernel](https://github.com/tya5/chrona/blob/f3688940/src/chrona/presentation/layout/lane_allocation.py) retains deterministic ordering and member identity, but the integrated insertion regression and public assignment evidence are not part of B1b-1. | [B1b-2/B2 plan](../../planning/active/issue-467-l3b-candidate-footprint-implementation-amendment-2026-09-27.md) |
| 4 | Deltas remain visible for packed items that have them. | deferred | [LaneMember](https://github.com/tya5/chrona/blob/f3688940/src/chrona/presentation/layout/lane_allocation.py) accepts measured member delta widths but B1b-1 does not map or render selected delta text. | [B1b-2/B2 plan](../../planning/active/issue-467-l3b-candidate-footprint-implementation-amendment-2026-09-27.md) |
| 5 | New Views and the packaged presets default to lanes; `automatic` still renders exactly as today. | deferred | [Public materializer CI](https://github.com/tya5/chrona/actions/runs/36301827524) shows no generated changes for the existing automatic corpus; no View or preset is changed and activation is reserved for L3c. | [L3c activation plan](../../planning/active/issue-467-494-l3-lane-completion-publication-amendment-2026-09-27.md) |
| 6 | At least three committed slides use lanes (for example `01`, `02` and `06`), and their evidence is reproducible. | deferred | [The B1b-1 publication plan](../../planning/active/issue-467-l3b-atomic-bundle-publication-amendment-2026-09-27.md) changes no slide resource and produces no public lane evidence. | [L3c activation plan](../../planning/active/issue-467-494-l3-lane-completion-publication-amendment-2026-09-27.md) |

### Issue #494

- Source: [Issue #494](https://github.com/tya5/chrona/issues/494)
- Observed: 2026-09-27

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | On `02-programme-board` (lanes), no relation is suppressed for `egress-collision`, and every remaining suppression is listed with a measured cause. | deferred | [B1b-1 allocator](https://github.com/tya5/chrona/blob/f3688940/src/chrona/presentation/layout/lane_allocation.py) does not compose routes or report route causes. | [B3 integration plan](../../planning/active/issue-467-494-l3b-prelayout-route-evidence-implementation-amendment-2026-09-27.md) |
| 2 | `test_lane_relation_routes_never_cross_a_required_lane_label` still passes on 02, 11 and 12: no route crosses any lane or member label. | deferred | [B1b-1 tests](https://github.com/tya5/chrona/blob/f3688940/tests/unit/chrona/presentation/layout/test_lane_allocation.py) produce no route or public lane slide. | [B3 integration plan](../../planning/active/issue-467-494-l3b-prelayout-route-evidence-implementation-amendment-2026-09-27.md) |
| 3 | Lane count and lane membership on 02 are unchanged, or any change is attributed. | deferred | [B1b-1 direct kernel](https://github.com/tya5/chrona/blob/f3688940/src/chrona/presentation/layout/lane_allocation.py) composes no 02 lane allocation; membership is therefore unmeasured by this slice. | [B2/B3 integration plan](../../planning/active/issue-467-l3b-candidate-footprint-implementation-amendment-2026-09-27.md) |

## Programme-level criteria (optional)

None beyond this partial B1b-1 kernel gate; the public issue criteria remain deferred.

## Architecture conclusion

The ownership boundary is appropriate for B1b-1: Layout receives already measured, renderer-neutral member footprints and decides lane admission and label placements. It does not read projection, source resources, Theme, or Scene, and it does not serialize output. The member-level overlay exception is explicit and local to a candidate bundle; it does not relax label collision checks or permit overlaps between separate candidates. The atomic result preserves source member identity and records visible overflow rather than dropping a required label.

This slice does not yet prove that those footprints represent every mark and required string in the Review projection. B1b-2 must supply closed bundles from projection facts; B2 must realize the plan once and establish the required row translation and public automatic-byte evidence at the integration seam; B3 must integrate route-cause evidence; L3c must activate lanes and produce public slide evidence. No issue is ready to close. All nine literal acceptance criteria remain deferred.
