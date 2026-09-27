# Design Plan — B1b-2 Comparison Facets and Actual Cutoff (#467, #494)

**Baseline:** fetched `origin/main` at `33fff72bff33255852b5dd575c8301819a34f631` (2026-09-27). **Triggered by:** the S2 mapper stop recorded during implementation exploration. **Predecessors:** [candidate-footprint design correction](../../design/issue-467-l3b-candidate-footprint-correction-2026-09-27.md), [B1b-2 stroke-aware design correction](../../design/issue-467-l3b-b1b-2-stroke-aware-footprint-correction-2026-09-27.md), [miter-envelope amendment](../../design/issue-467-l3b-b1b-2-miter-envelope-amendment-2026-09-27.md), and [B1b-2 implementation plan](issue-467-l3b-b1b-2-stroke-aware-footprint-implementation-plan-amendment-2026-09-27.md). This is a discovery plan only: no API, schema, or behavior is selected and no product code is authorized.

## Published baseline and exact gap

### Verified published facts

- The candidate-footprint correction says a same-object comparison/Actual facet contributes footprint and provenance but is not another lane-table item or duplicate required name. An attached point remains its own named/countable item pinned to its host candidate's lane.
- In `src/chrona/presentation/layout/lane_allocation.py`, `LaneCandidate.bundle` is a tuple of `LaneMember`s. `_Lane.accept()` appends every member ID to `LaneAssignment.members`; `lane_of()` also finds candidates through that list.
- In `src/chrona/presentation/layout/lane_preflight.py`, the optional lane-table count is `len(lane.members)`. Therefore representing a comparison facet as an ordinary `LaneMember` increases the displayed count.
- `LaneMark.footprints` holds anonymous `ObstacleGeometry` values. It has no source or primitive identity/port field. Combining a comparison facet there cannot by itself retain its required source identity and port association for later composition.
- `ReviewItem` contains Actual values, including `openUntil: "asOf"`, while `ReviewProjection` has no `as_of` field. `build_review_projection()` reads the Actual Set cutoff to derive observation state and then returns a projection without that date. `surface_composer.py` later uses `contract.time.as_of` to complete open Actual geometry. The B1b-2 mapper plan requires that geometry to be closed before final block resolution.
- The public issue pages for [#467](https://github.com/tya5/chrona/issues/467) and [#494](https://github.com/tya5/chrona/issues/494) show no later comments as of this baseline read. Their literal acceptance criteria are copied below; all remain issue-level criteria, not this plan's acceptance.
- Lane mode remains guarded from public projection/rendering. B1b-2 is a direct Layout seam; B2 composition, B3 route-cause integration and L3c activation remain later units.

### Inferences and unverified points

- A mapper that emits comparison facets as ordinary bundle members appears incompatible with the published lane count contract. This follows from the allocator and preflight code above; no user-visible lane count has yet been produced by this mapper.
- A mapper that flattens comparison geometry into an anonymous root footprint appears unable to hand B2 the exact source-to-primitive/port provenance needed to realize the selected mark set. The end-to-end necessity and minimum representation are to be confirmed against Scene request transport and the composer.
- Supplying `as_of` directly to Layout, retaining it in `ReviewProjection`, or supplying a small immutable temporal-facts input may each close the open-Actual seam. Ownership, serialization, and compatibility effects have not been reviewed.
- No lane mapping or #02 feasibility evidence establishes whether the exact selected representation will keep the ≤12-lane gate after the approved 10× path envelope.

## Objective and design boundary

Define a reviewable Layout input/output contract that preserves comparison source/primitive identity and ports without adding comparison facets to lane-table item counts, keeps attached points independently named and countable, and supplies the selected Actual cutoff before candidate closure. Review the contract across projection, allocator/preflight, composer, Scene transport, and the adjacent specifications before amending the implementation plan.

This plan does not choose the representation, change projection or serialized schemas, implement the mapper, activate lane mode, change route policy, or claim issue acceptance. Any normative identity/count or source-closure change must be recorded in a successor design correction and reviewed before implementation planning is finalized.

## Use cases to resolve

1. One host candidate has planned geometry and one or more same-object snapshot/scenario/Actual visual facets, each with stable source and primitive identities and usable ports, while the lane table counts the selected host once.
2. An attached point is an independently identified/countable bundle member with its own mark, port and measured title/date/delta; it is pinned to the host lane and sorted deterministically.
3. A closed Actual, point Actual, open Actual, missing Actual, comparison overlay, progress inset, and selected icon close from facts available before the final block solve. An open Actual ends at the selected Actual Set cutoff.
4. Lane-member count, representative identity, first-fit/predecessor lookup, diagnostics, and public lane-table cells agree on which identities represent selected items versus visual facets.
5. Automatic and explicit composition retain their existing behavior and bytes; the public lane guard remains closed throughout B1b-2.

## Responsibility boundaries

- Projection/Review owns selected source rows, item identities, attachment intent, comparison selection, and Actual observation facts. The design must establish where the selected cutoff is carried so it is available to Layout without turning Layout into a resource loader.
- Layout owns conversion to measured marks, stroke-aware footprints, lane assignment, and preflight identity/count outputs. It must retain enough provenance for B2 to realize precisely the preflighted geometry.
- Theme and normalized icon closure supply validated geometry metrics and paths. They do not decide lane-table item count or source identity.
- Scene projects completed Layout geometry and source identity; adapters serialize it. Neither reconstructs a facet nor repairs its port or geometry.
- The neutral allocator remains free of Project/View resource loading and paint conversion. Route and quality policies remain unchanged.

## Alternatives and open questions

These are candidates for D1 review, not decisions:

1. Extend the mark geometry value with immutable source-keyed visual facets (including primitive/port provenance), leaving only countable Review items in `LaneMember`; versus introduce explicitly non-counting facet members and make all count/representative/predecessor semantics operate on a declared item-identity set.
2. Return candidate bundles with a parallel immutable provenance map; versus carry provenance within the completed Layout mark value. In either case, determine how allocator collision checks and B2 consume the same geometry exactly once.
3. Carry cutoff in `ReviewProjection`; versus pass a validated immutable Actual-time fact alongside projection. Confirm whether other projection-derived facts would then be duplicated or inconsistently sourced.
4. Define stable typed failures for absent cutoff, facet geometry/provenance, or inconsistent item-count identity; confirm how existing Theme diagnostics propagate without being converted into “no lane fits.”
5. Determine which identities feed lane representative labels, table counts, predecessor lookup, allocation placements, and routing ports when visual facets share one semantic source object.

## Planned design and review slices

| Slice | Work and owners | Evidence and exit condition | Publication boundary |
|---|---|---|---|
| **D0 — source trace** | Trace comparison and Actual membership from `_compose_rows`/projection through allocator, `lane_preflight`, `surface_composer`, Scene request/result and adapters; trace selected Actual Set cutoff from render input to open-Actual geometry. | Source-to-candidate-to-mark/port identity map; exact count derivation; exact cutoff ownership; record published facts, inferred risks, and gaps. | This plan records the initial gap. Correct any source-trace error in a successor amendment before choosing behavior. |
| **D1 — contract design** | Specify countable item identity, facet provenance, overlay pair declaration, ownership of cutoff facts, stable ordering/representative/predecessor behavior, typed failures, and one-time geometry handoff. Check attached points and multi-facet hosts. | A complete immutable input/result contract proves every visible source facet can be realized once and every selected item is counted once; no labels are exempted and no facet becomes an independent lane candidate. | Publish a dated design correction; update Specification 38 and any other normative home if identity/count semantics change. |
| **D2 — whole-architecture review** | Review Specifications 38/46/50, #486 attachment, #480 row sizing, #481 group bands, #487 table measurement, #466 obstacle/route priority, S1 Layout geometry, Scene paint/projection, and SVG/PNG/PDF/Typst/TikZ materializers. | Consistency table, selected alternative and rejected options, migration/compatibility impact, unresolved risks, and explicit confirmation that 10× path bounds and separate clearance remain intact. | Publish architecture review before the implementation plan is treated as final. |
| **D3 — S2 implementation amendment** | Name exact Layout and any Review/projection owners; specify mapper and provenance types, neutral fixtures, integration seam, tests, byte/materializer evidence, and public guard. | Independent S2 slice with acceptance for host+facet+attached bundle, item counts, stable identities/ports, selected cutoff/open Actual, deterministic order and typed failures. | Publish implementation amendment before product code; keep B2/B3/L3c as later publication boundaries. |

## Acceptance evidence required from implementation

- Neutral host-plus-comparison-plus-attached fixtures verify exact countable identities, all source identities/ports, allowed overlay pairs, independent attached labels, deterministic insertion/order and one-lane pinning.
- Fixtures cover closed/open/point/missing Actual and progress; open geometry uses the selected cutoff. Missing cutoff or source/geometry data fails with the approved typed diagnostic before allocation.
- Direct geometry-parity checks cover Theme mark roles, point/glyph/icon completion, path control-point envelope at 10× stroke width per side, segment stroke carrier, rectangle expansion, clipped progress, and separate collision clearance. No stroke is counted twice.
- Mapper-to-allocator-to-preflight tests verify lane member lists, representatives, predecessor lookup, and lane-table counts agree with the approved countable identity set.
- B2-facing provenance evidence proves each comparison primitive and port is realized once from the same completed geometry used for collision checks.
- Existing automatic/explicit Scene and SVG outputs are byte-characterized; affected public materializers and rendered geometry are inspected as a batch. Lane mode remains fail-closed; no public activation or issue-level acceptance is inferred.

## Literal issue acceptance retained

Copied verbatim from the current issue bodies. All rows remain open and are not claimed by this discovery plan.

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

## Successor and publication boundary

After D1, publish a design correction linked to this plan. At design completion, publish the whole-architecture review and any normative specification update. Then publish the S2 implementation amendment. All nine issue criteria remain open until a later acceptance review supplies direct evidence. Publish serially from a rechecked `origin/main`; do not push this plan as part of the requested local draft.
