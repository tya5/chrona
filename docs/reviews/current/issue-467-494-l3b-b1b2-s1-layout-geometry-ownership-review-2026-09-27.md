<!-- chrona:literal-acceptance/v1 -->

# B1b-2 S1 Implementation Review — Layout Geometry Ownership (#467, #494)

**Reviewed base:** public `7c1bf4d9` (`refactor: complete mark and icon paths in layout`), corrected by public `33fff72b` (ownership and diagnostic gates). **Reviewed implementation:** commits `7c1bf4d9` and `33fff72b`, plus independent import/reachability and focused verification. **Plan:** [B1b-2 implementation amendment](../../planning/active/issue-467-l3b-b1b-2-stroke-aware-footprint-implementation-plan-amendment-2026-09-27.md). **Status:** S1 is accepted as a Layout geometry ownership seam; all nine #467/#494 issue criteria remain deferred. This review does not accept lane composition or support closing either issue.

## Scope and findings

S1 moves selected mark and icon path construction into Layout before obstacle allocation. `layout/mark_geometry.py` and `layout/icon_geometry.py` now produce completed geometry; `surface_composer.py` supplies it to Scene. Scene no longer imports the removed `scene/mark_geometry.py` implementation or constructs those mark/icon paths in `v05_builder.py`. Paint resolution remains in `ScenePaintResolver`; Layout consults Theme for shape selection and geometry metrics, without converting resolved paint. The semantic stroke-binding presence query and stroke-aware candidate footprint are S2 work, not S1 evidence. The module reachability/import check confirms the ownership direction.

This matches the plan's responsibility boundary: Layout owns completed geometry and footprint inputs, Scene selects/projects primitive identity and order, and adapters serialize. The review found the key compatibility cases covered by characterization: point and point-legend swatches, glyph contain-center and the built-in diamond override distinction, `paint:none`, part IDs/order, close-point conversion, float arithmetic, vector cap/join and scaled stroke, raster viewport, and normalized icon path identity. The published stroke footprint contract specifies rectangle expansion at half-width, segment width in its obstacle record, stroked path control-point envelopes at ten widths per side, and fill-only paths unexpanded; S1 has not yet applied those rules to lane candidates. Collision clearance remains a separate concern.

The S1 tests reported by the implementer pass in two batches: 149 focused tests, and an additional 60 focused tests plus import/reachability checks. The public materializer check passed for all 28 slides. Across the 56 generated files, recorded byte hashes are unchanged; no generated outputs or resource/schema mirrors changed. These establish current automatic/explicit artifact compatibility for this seam, not lane-mode output correctness.

CI run [36304448357](https://github.com/tya5/chrona/actions/runs/36304448357) failed on all three OSes from a stale diagnostic inventory, stale Scene-field delivery manifest, and one renderer test importing the removed module; newest-Python reproduction passed. Corrective commit `33fff72b` refreshed those gates and the import. Its [run 36304959026](https://github.com/tya5/chrona/actions/runs/36304959026) passed three-OS conformance/full pytest/wheel-smoke and newest-Python reproduction. The corrected release gate is complete.

## Architecture and limits

The ownership move is coherent across Layout, Theme token inspection, Scene paint resolution, and adapter serialization. In particular, Scene no longer owns geometry derivation, and Layout does not take on paint conversion. The S1 slice introduces no schema or resource migration and leaves the public lane-mode guard in place.

This review accepts only the direct geometry ownership seam. It does not prove the future mapper emits a complete bundle for every projected mark, that stroke-expanded footprints match a composed lane plan end to end, that a shared preflight/final composition consumes one immutable plan, or that routed relations satisfy #494. S2 remains the next independently reviewable slice: projection-to-atomic-bundle mapping in Layout, with direct parity tests, complete mark inventory, overlay and identity checks, and fail-closed behavior. Keep B2 composition, B3 route evidence and L3c public activation behind their published gates.

## Literal issue acceptance

### Issue #467

- Source: [Issue #467](https://github.com/tya5/chrona/issues/467)
- Observed: 2026-09-27

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | A lane row mode exists. On `02-programme-board` the 26 items occupy at most 12 lanes, with the chain `structure → avionics → bus-test` on one lane. | deferred | S1 moves geometry construction into Layout but does not map projected items into lane bundles or compose 02. The [public lane guard](../../../src/chrona/usecases/render_review.py) remains closed. | [B1b-2 S2 and later composition gates](../../planning/active/issue-467-l3b-b1b-2-stroke-aware-footprint-implementation-plan-amendment-2026-09-27.md) |
| 2 | Every packed task and milestone has a visible name on the slide; no `W_LAYOUT_LABEL_SUPPRESSED` for a packed item on any committed slide. | deferred | S1 does not create or render packed lane labels; [28 current public materializers](../../planning/active/issue-467-l3b-b1b-2-stroke-aware-footprint-implementation-plan-amendment-2026-09-27.md) reproduce unchanged. | [B1b-2 S2 and L3c activation gate](../../planning/active/issue-467-l3b-b1b-2-stroke-aware-footprint-implementation-plan-amendment-2026-09-27.md) |
| 3 | Lane assignment is deterministic, and a test shows that one inserted item does not reorder unrelated lanes. | deferred | S1 does not integrate the allocator with projected items. The [focused test scope](../../planning/active/issue-467-l3b-b1b-2-stroke-aware-footprint-implementation-plan-amendment-2026-09-27.md) covers geometry ownership and compatibility, not end-to-end lane assignment. | [B1b-2 S2 and B2 composition gate](../../planning/active/issue-467-l3b-b1b-2-stroke-aware-footprint-implementation-plan-amendment-2026-09-27.md) |
| 4 | Deltas remain visible for packed items that have them. | deferred | S1 does not map or compose lane labels or deltas; see the [S1 boundary](../../planning/active/issue-467-l3b-b1b-2-stroke-aware-footprint-implementation-plan-amendment-2026-09-27.md). | [B1b-2 S2 and L3c activation gate](../../planning/active/issue-467-l3b-b1b-2-stroke-aware-footprint-implementation-plan-amendment-2026-09-27.md) |
| 5 | New Views and the packaged presets default to lanes; `automatic` still renders exactly as today. | deferred | No View or preset migration occurs in S1. The [28-slide materializer check and 56 generated-file hashes](../../planning/active/issue-467-l3b-b1b-2-stroke-aware-footprint-implementation-plan-amendment-2026-09-27.md) characterize current public output only. | [L3c public activation gate](../../planning/active/issue-467-l3b-b1b-2-stroke-aware-footprint-implementation-plan-amendment-2026-09-27.md) |
| 6 | At least three committed slides use lanes (for example `01`, `02` and `06`), and their evidence is reproducible. | deferred | S1 publishes no lane slides or lane materializer evidence; see the [S1 publication boundary](../../planning/active/issue-467-l3b-b1b-2-stroke-aware-footprint-implementation-plan-amendment-2026-09-27.md). | [L3c public activation gate](../../planning/active/issue-467-l3b-b1b-2-stroke-aware-footprint-implementation-plan-amendment-2026-09-27.md) |

### Issue #494

- Source: [Issue #494](https://github.com/tya5/chrona/issues/494)
- Observed: 2026-09-27

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | On `02-programme-board` (lanes), no relation is suppressed for `egress-collision`, and every remaining suppression is listed with a measured cause. | deferred | S1 has no lane relation-routing integration or route-cause inventory; see the [B3 boundary](../../planning/active/issue-467-l3b-b1b-2-stroke-aware-footprint-implementation-plan-amendment-2026-09-27.md). | [B3 route-evidence gate](../../planning/active/issue-467-l3b-b1b-2-stroke-aware-footprint-implementation-plan-amendment-2026-09-27.md) |
| 2 | `test_lane_relation_routes_never_cross_a_required_lane_label` still passes on 02, 11 and 12: no route crosses any lane or member label. | deferred | S1 changes mark/icon geometry ownership only; it does not route relations or produce lane renders for 02, 11 and 12. See the [S1 scope](../../planning/active/issue-467-l3b-b1b-2-stroke-aware-footprint-implementation-plan-amendment-2026-09-27.md). | [B3 route-evidence gate](../../planning/active/issue-467-l3b-b1b-2-stroke-aware-footprint-implementation-plan-amendment-2026-09-27.md) |
| 3 | Lane count and lane membership on 02 are unchanged, or any change is attributed. | deferred | S1 neither composes nor changes 02 lane membership; it establishes no current lane count. See the [B2 scope](../../planning/active/issue-467-l3b-b1b-2-stroke-aware-footprint-implementation-plan-amendment-2026-09-27.md). | [B2 composition and B3 route-evidence gates](../../planning/active/issue-467-l3b-b1b-2-stroke-aware-footprint-implementation-plan-amendment-2026-09-27.md) |

## Programme-level criteria (optional)

| Slice criterion | Disposition | Evidence |
| --- | --- | --- |
| Geometry/path construction is Layout-owned while Scene paint resolution remains authoritative. | met for S1 | Layout geometry modules and composer handoff; Scene-side geometry implementation removed; focused import/reachability check reported passing. |
| Existing public materializers retain their generated bytes. | met for S1 | 28-slide materializer check passed; 56 generated-file hashes unchanged. |
| CI release evidence is complete. | met for S1 | Initial [run 36304448357](https://github.com/tya5/chrona/actions/runs/36304448357) failed on three S1 gate-maintenance omissions; corrective `33fff72b` and [run 36304959026](https://github.com/tya5/chrona/actions/runs/36304959026) passed the full planned matrix. |

**Disposition:** Accept S1 as a partial Layout ownership migration at public base `33fff72b` with its corrected CI gate. Keep #467 and #494 open. S2 is next but paused for the comparison-facet count/provenance and Actual-cutoff design correction; S1 supplies completed geometry constructors, not the semantic stroke-binding query or lane mapper.
