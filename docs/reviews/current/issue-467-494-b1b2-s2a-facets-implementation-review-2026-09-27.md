<!-- chrona:literal-acceptance/v1 -->

# B1b-2 S2a Implementation Review — Source-Keyed Lane Facets (#467, #494)

**Public base reviewed:** `7288f7f8cf80fa4fe660b8ca6bc918cbbeacfea8` (`origin/main`). **Product commits:** `1ba5880681b52e5d6e172b9794f115a84186ee99` and `7288f7f8cf80fa4fe660b8ca6bc918cbbeacfea8`. **Plan:** [S2 implementation amendment](../../planning/active/issue-467-b1b2-facet-count-asof-implementation-plan-amendment-2026-09-27.md). **Status:** S2a is accepted as a direct Layout allocator/facet-model slice. All nine #467/#494 issue criteria remain deferred; this review does not support closing either issue.

## Implementation and boundary

S2a adds immutable `LaneFacetPort` and `LaneMarkFacet` values in Layout. A facet keeps projection-instance and source identity distinct, associates completed primitive geometry and bounds with its visible collision footprint, and carries typed ports and explicitly named overlay peers. `LaneMark.facets` is now the source of truth; `.footprints` is derived from those facets. Candidate/bundle validation rejects missing facets, duplicate facet or port IDs, unknown overlay targets, invalid geometry/ports, and undeclared within-bundle footprint collisions. `LaneMember` continues to represent one countable root or attached Review item, so comparison facets do not inflate membership, lane-table counts or label placements.

This matches the S2a contract and preserves the Layout boundary. The new types are neutral: no Project, View, Theme, Scene or adapter resource loading was added to the allocator. The public lane-mode guard remains in [`render_review.py`](../../../src/chrona/usecases/render_review.py). Therefore the slice establishes an allocator data contract, not a projection mapper or a rendered-lane result.

## Verification evidence

- Focused S2a allocation/preflight selection: **33 passed**.
- Public materializers: `tools/regenerate_public_examples.py --check` passed for **28 slides**, with generated output unchanged.
- Diagnostic inventory and module-reachability checks passed; the inventory includes the new `lane_allocation.py` validation sites.
- No schema, resource, preset or generated public artifact migration is part of this slice.
- CI [run 36306880471](https://github.com/tya5/chrona/actions/runs/36306880471) completed successfully: Ubuntu, macOS and Windows conformance jobs and newest-Python public-materializer reproduction are green.

The focused fixtures cover explicit facet overlays, rejecting unapproved overlap, one-count-per-root/attached-item behavior, repeated source references in separate projection instances, unique ports, primitive/visible-footprint bounds, and rejection of incomplete marks. They also preserve stable allocator membership behavior. These tests characterize the facet model and allocator use, not the S2b mapper's completeness or downstream B2 realization.

## Architecture conclusion and next slice

The implementation's responsibility split is sound: Layout owns collision geometry and provenance; comparison/Actual visuals remain facets of selected countable members; labels/routes receive no overlay exemption. The explicit overlay IDs make the exception local and reviewable, while the facet sequence remains the only footprint source for collision queries.

The principal remaining seam is S2b: map a closed `ReviewProjection`, selected `as_of`, Theme-derived Layout geometry, icon facts, temporal scale and measured labels into complete source-keyed candidate bundles, then close preflight over that output. S2a alone cannot prove each real projected primitive's geometry/footprint parity, open-Actual cutoff behavior, port provenance through composition, 02 lane feasibility, or route behavior. The S2 amendment assigns these to S2b and keeps B2 realization, B3 route evidence and L3c activation as separate later gates.

## Literal issue acceptance

### Issue #467

- Source: [Issue #467](https://github.com/tya5/chrona/issues/467)
- Observed: 2026-09-27

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | A lane row mode exists. On 02-programme-board the 26 items occupy at most 14 lanes, with the chain structure → avionics → bus-test on one lane. The acceptance review lists the lane count and attributes every lane above 10 to its cause: a mark or label collision, or a chain rule. (Amended 2026-09-27: was "at most 12"; see the comment.) | deferred | S2a only supplies the [neutral facet allocator contract](../../../src/chrona/presentation/layout/lane_allocation.py); it does not map or compose 02, and the [public guard](../../../src/chrona/usecases/render_review.py) remains closed. The owner-approved threshold change does not change S2a's scope or provide the required lane count/cause evidence. | [S2b mapper/preflight and later composition gates](../../planning/active/issue-467-b1b2-facet-count-asof-implementation-plan-amendment-2026-09-27.md) |
| 2 | Every packed task and milestone has a visible name on the slide; no `W_LAYOUT_LABEL_SUPPRESSED` for a packed item on any committed slide. | deferred | S2a produces no packed slide or required lane labels; the [S2a-to-S2b plan boundary](../../planning/active/issue-467-b1b2-facet-count-asof-implementation-plan-amendment-2026-09-27.md) leaves mapping for the next slice. | [S2b mapper/preflight and L3c activation gate](../../planning/active/issue-467-b1b2-facet-count-asof-implementation-plan-amendment-2026-09-27.md) |
| 3 | Lane assignment is deterministic, and a test shows that one inserted item does not reorder unrelated lanes. | deferred | S2a preserves neutral allocator tests and deterministic member identities, but has no integrated projection-to-lane mapping; see the [S2b acceptance scope](../../planning/active/issue-467-b1b2-facet-count-asof-implementation-plan-amendment-2026-09-27.md). | [S2b mapper/preflight gate](../../planning/active/issue-467-b1b2-facet-count-asof-implementation-plan-amendment-2026-09-27.md) |
| 4 | Deltas remain visible for packed items that have them. | deferred | S2a does not map or compose packed labels/deltas; see the [S2b mapper scope](../../planning/active/issue-467-b1b2-facet-count-asof-implementation-plan-amendment-2026-09-27.md). | [S2b mapper/preflight and L3c activation gate](../../planning/active/issue-467-b1b2-facet-count-asof-implementation-plan-amendment-2026-09-27.md) |
| 5 | New Views and the packaged presets default to lanes; `automatic` still renders exactly as today. | deferred | S2a performs no View/preset migration. The [28-slide public materializer check](../../planning/active/issue-467-b1b2-facet-count-asof-implementation-plan-amendment-2026-09-27.md) is unchanged and characterizes current public artifacts only. | [L3c public activation gate](../../planning/active/issue-467-b1b2-facet-count-asof-implementation-plan-amendment-2026-09-27.md) |
| 6 | At least three committed slides use lanes (for example `01`, `02` and `06`), and their evidence is reproducible. | deferred | S2a produces no lane slides or rendered evidence; see the [published activation boundary](../../planning/active/issue-467-b1b2-facet-count-asof-implementation-plan-amendment-2026-09-27.md). | [L3c public activation gate](../../planning/active/issue-467-b1b2-facet-count-asof-implementation-plan-amendment-2026-09-27.md) |

### Issue #494

- Source: [Issue #494](https://github.com/tya5/chrona/issues/494)
- Observed: 2026-09-27

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | On `02-programme-board` (lanes), no relation is suppressed for `egress-collision`, and every remaining suppression is listed with a measured cause. | deferred | S2a has no route integration or suppression-cause inventory; the [S2 amendment](../../planning/active/issue-467-b1b2-facet-count-asof-implementation-plan-amendment-2026-09-27.md) assigns route evidence to B3. | [B3 route-evidence gate](../../planning/active/issue-467-b1b2-facet-count-asof-implementation-plan-amendment-2026-09-27.md) |
| 2 | `test_lane_relation_routes_never_cross_a_required_lane_label` still passes on 02, 11 and 12: no route crosses any lane or member label. | deferred | S2a does not compose/reroute 02, 11 or 12; the [published plan](../../planning/active/issue-467-b1b2-facet-count-asof-implementation-plan-amendment-2026-09-27.md) places this evidence in B3. | [B3 route-evidence gate](../../planning/active/issue-467-b1b2-facet-count-asof-implementation-plan-amendment-2026-09-27.md) |
| 3 | Lane count and lane membership on 02 are unchanged, or any change is attributed. | deferred | S2a changes allocator facet inputs but does not create a 02 projection-to-bundle mapping; the [S2b and B2 boundary](../../planning/active/issue-467-b1b2-facet-count-asof-implementation-plan-amendment-2026-09-27.md) remains. | [S2b mapper and B2 composition gates](../../planning/active/issue-467-b1b2-facet-count-asof-implementation-plan-amendment-2026-09-27.md) |

## Programme-level criteria (optional)

| Slice criterion | Disposition | Evidence |
| --- | --- | --- |
| Source-keyed completed facets are the allocator's footprint source; only explicit facet pairs may overlap within a bundle. | met for S2a | [`LaneMarkFacet`, `LaneMark`, and bundle validation](../../../src/chrona/presentation/layout/lane_allocation.py); focused tests passed. |
| Countable lane membership remains root/attached Review items, not visual comparison facets. | met for S2a | [`LaneMember` and allocation membership tests](../../../tests/unit/chrona/presentation/layout/test_lane_allocation.py); focused selection passed (33 tests). |
| Current public materializers and diagnostic/reachability checks pass. | met for S2a | [Public materializer command and planned evidence gates](../../planning/active/issue-467-b1b2-facet-count-asof-implementation-plan-amendment-2026-09-27.md); 28 slides unchanged, diagnostic inventory and module reachability passed. |
| Planned CI conformance and newest-Python public-materializer evidence is complete. | met for S2a | [Run 36306880471](https://github.com/tya5/chrona/actions/runs/36306880471) passed Ubuntu/macOS/Windows conformance and newest-Python reproduction. |

**Disposition:** Accept S2a as the direct source-keyed facet/allocation slice. Keep #467 and #494 open and keep public lane mode closed. S2b mapper/preflight closure is next; the planned CI conformance and newest-Python reproduction gate is green on run `36306880471`.
