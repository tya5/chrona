# Architecture Review — Counted Lane Members, Source-Keyed Facets, and Actual Cutoff (#467, #494)

**Decision:** approve the [design correction](../../design/issue-467-b1b2-facet-count-asof-design-correction-2026-09-27.md) as the contract for an amended B1b-2 implementation plan. This review accepts no implementation, lane activation, or issue-level acceptance. **Plan:** [discovery plan](../../planning/active/issue-467-b1b2-facet-count-asof-design-plan-2026-09-27.md). **Base:** `d371bd21efeedd13f90674006ca9c75ca7461807`.

## Whole-architecture consistency

| Boundary | Finding |
|---|---|
| Projection and Specification 38 | The chosen contract preserves one selected Review item as one countable member. Comparison/Actual visual facets retain projection-instance identity (row/item or automatic projected instance) and stable source reference without becoming duplicate lane-table items or required names. Repeated source/object pairs in different explicit rows keep distinct facet and port identities, consistent with §1–2's row/item identity and ambiguous-anchor rules. Attached points remain separate named/countable items in their host bundle. This clarifies, rather than reverses, the existing §3.1 distinction. The cutoff remains a render-time presentation fact; no Projection or serialized schema change is needed. |
| `PresentationContract` and Actual | `PresentationContract.time.as_of` already provides the selected cutoff to Layout. Passing that validated date explicitly to the mapper preserves one cutoff authority and keeps Actual resource resolution outside Layout. An open Actual without the cutoff cannot produce a bounded mark and therefore fails with the approved Layout footprint diagnostic before allocation. |
| B1b allocator and preflight | Current `accept()` appends each `LaneMember` to `LaneAssignment.members`, and lane-table counts use `len(lane.members)`. Restricting `LaneMember` to countable root/attached items makes those existing meanings coherent. Facet collision geometry/provenance remains attached to the countable member so a comparison does not get a second candidate, label, or count. The implementation amendment must identify any allocator changes needed to validate facet-level collisions and overlay pairs, with exact projection-instance and source-port maps preserved into B2. |
| Theme, Layout geometry, and icon closure | Layout owns completed mark/path/icon geometry and measured footprints. Each immutable facet ties the source and primitive identity to completed geometry, footprint and ports, allowing stroke expansion exactly once. The existing 10× path-control-point envelope remains; segment stroke width and rectangle expansion retain their distinct carriers; clearance stays separate. Theme paint conversion remains outside the mapper. |
| #486, #480, #481 and #487 | Attached points remain independently measured labels and countable items while sharing the root lane. Lane natural extent, required table text-line block, group bands and measured columns remain later B2 responsibilities and consume the same completed plan. This design does not alter row-height or table-measurement formulas. |
| #466, Specification 50, Scene and adapters | Routes continue to see all required labels and every source-facet footprint; overlay declarations do not exempt routes or labels. Scene projects completed geometry/ports and resolves paint; adapters serialize. No renderer-specific geometry or miter policy is added. Automatic/explicit output is byte-characterized and remains unchanged. |

## Alternatives and risks

The review rejects counted comparison members, anonymous root footprints, parallel provenance that can drift from the collision geometry, duplicating the cutoff in Projection, and Scene-side reconstruction. The accepted source-keyed facet value makes the collision representation and B2 source provenance one immutable record while retaining the existing countable-member model.

Remaining implementation risks are the precise facet-level allocator collision/overlay validation API, stable primitive and port IDs through B2/Scene transport, and the effect of complete facet geometry plus the 10× path envelope on the hard 02 lane-count/chain gate. These require direct tests and current-data rendered evidence; this design does not claim their results. If an admitted primitive cannot retain a collision footprint and B2 projection identity in one immutable facet, implementation must stop and return to design.

## Publication and acceptance disposition

Specification 38 §3.1 is updated by this review's design correction. No adjacent normative specification needs a semantic change: Specifications 46 and 50 already assign paint conversion and completed placement/route responsibility to the existing layers, and the correction stays within those contracts. The next publication is an amended B1b-2 implementation plan naming the facet value, allocator/preflight integration, fixtures, typed failures, generated/public materializer evidence, and review boundary. B2, B3 and L3c remain separate later units.

All literal issue criteria remain deferred by this design/review:

### Issue #467

- [ ] A lane row mode exists. On `02-programme-board` the 26 items occupy at most 12 lanes, with the chain `structure → avionics → bus-test` on one lane.
- [ ] Every packed task and milestone has a visible name on the slide; no `W_LAYOUT_LABEL_SUPPRESSED` for a packed item on any committed slide.
- [ ] Lane assignment is deterministic, and a test shows that one inserted item does not reorder unrelated lanes.
- [ ] Deltas remain visible for packed items that have them.
- [ ] New Views and the packaged presets default to lanes; `automatic` still renders exactly as today.
- [ ] At least three committed slides use lanes (for example `01`, `02` and `06`), and their evidence is reproducible.

### Issue #494

- [ ] On `02-programme-board` (lanes), no relation is suppressed for `egress-collision`, and every remaining suppression is listed with a measured cause.
- [ ] `test_lane_relation_routes_never_cross_a_required_lane_label` still passes on 02, 11 and 12: no route crosses any lane or member label.
- [ ] Lane count and lane membership on 02 are unchanged, or any change is attributed.
