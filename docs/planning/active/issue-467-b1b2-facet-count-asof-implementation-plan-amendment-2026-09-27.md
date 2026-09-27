# Implementation Plan Amendment — B1b-2 Source-Keyed Facets and Actual Cutoff (#467, #494)

**Base:** `e202dbd9fe898a5f61aaf8c1cfbdef3f4cba98cf`. **Amends:** [stroke-aware B1b-2 implementation plan](issue-467-l3b-b1b-2-stroke-aware-footprint-implementation-plan-amendment-2026-09-27.md). **Design authority:** [facet/count/cutoff correction](../../design/issue-467-b1b2-facet-count-asof-design-correction-2026-09-27.md), [whole-architecture review](../../reviews/current/issue-467-b1b2-facet-count-asof-architecture-review-2026-09-27.md), and [Specification 38 §3.1](../../specification/38-review-row-composition.md). This authorizes only the direct S2 Layout mapper seam. It does not wire B2 composition, remove the public lane guard, or activate lane mode.

## S2 implementation slices

| Slice | Owners and files | Acceptance evidence | Publication boundary |
|---|---|---|---|
| **S2a — source-keyed facet model and allocation** | `presentation/layout/lane_allocation.py`; tests in `tests/unit/chrona/presentation/layout/test_lane_allocation.py`. Add immutable Layout types `LaneFacetPort` and `LaneMarkFacet`. A facet identifies one emitted primitive by projection-instance ID, source item ID/reference, source kind, semantic role and primitive/part ID/type; it carries completed Layout geometry, its visible collision footprint, typed ports, and explicit `overlay_with` facet IDs. `LaneMark.facets` becomes the source of truth; the current anonymous `.footprints` access is retained only as a derived tuple/property for allocator collision queries. Validate unique/stable IDs, known facet overlay targets, exact footprint/geometry association, finite ports/coordinates, and internal collisions. An overlap is legal only for its explicitly named facet pair in this same candidate bundle. `LaneMember` remains countable: its `member_id` is one selected root/host or attached Review item. Remove/stop using member-level comparison overlay identities; comparison/Actual marks are facets under the relevant countable member. `LaneAssignment.members`, placements used as item membership, predecessor lookup and `lane_of()` continue to contain only root/attached item IDs. | Neutral tests prove source vs projection-instance identity, repeated same source/object in distinct explicit rows, every primitive facet retained once, explicit overlay pair acceptance and undeclared-overlap rejection, attached/root countability, stable representative/predecessor behavior and no label/route exemption. Verify `LaneMark` footprint derivation cannot omit or double-expand a facet. | Publish the allocator/facet model only after old allocator tests and new invariants pass. Keep public mode closed. |
| **S2b — mapper and preflight closure** | New `presentation/layout/lane_bundle_mapper.py`; `lane_preflight.py`; tests in new `tests/unit/chrona/presentation/layout/test_lane_bundle_mapper.py` and `test_lane_preflight.py`. Mapper inputs: closed `ReviewProjection`, explicit `as_of: date | None` forwarded from the existing `PresentationContract.time.as_of`, lane intent, resolved Theme mark geometry, normalized icon/visual facts, exact seed temporal scale, and once-measured label widths/font identity. Output: deterministic `LaneCandidate`/countable `LaneMember` bundles whose `LaneMark.facets` hold each selected mark visual and source port. Do not load Project/View/Actual resources, Scene paint, or copy `as_of` into projection. Open Actual with `openUntil: "asOf"` requires `as_of`; absent cutoff or unavailable/invalid selected geometry fails before allocation with `LayoutError("E_LAYOUT_LANE_FOOTPRINT_UNAVAILABLE", source_path, ...)`, while existing invalid Theme diagnostics propagate unchanged. | Direct role-to-geometry parity for every mark class below; focused mapper→allocator→preflight fixture verifies lane member lists/table counts count only selected root/attached items, comparison facets add no label/count, exact port/facet provenance remains available to B2, and one immutable completed geometry set drives collision. Deterministic insertion/order and attached-point single-lane pinning are required. | Publish S2 mapping only after focused tests and the public-materializer/automatic-byte batch below pass. All nine issue criteria remain deferred. |
| **S2c — ownership and regression evidence** | Existing S1 owners `layout/mark_geometry.py`, `layout/icon_geometry.py`, `layout/path_geometry.py`, `surface_composer.py`, `scene/v05_builder.py`, and their current tests; add only focused parity fixtures where S2 uncovers a needed seam. No serialized schema/resource migration is planned. | Prove Layout facet geometry equals the exact completed geometry that a later B2 projection must consume. Scene does not rebuild geometry, paths, strokes, ports or scale. Capture and byte-compare automatic and explicit Scene/SVG baselines; inspect the supported public materializer batch and generated evidence. | Review S2 as a direct seam; keep B2 one-plan realization, B3 route evidence, and L3c activation as separate later publication/review units. |

## Required geometry matrix

Tests compare source-keyed facet geometry with Layout's existing constructors and emitted primitive inventory; each collision footprint is derived once and clearance remains separate.

- Planned span `Rect` and planned point built-in symbol or Theme glyph parts, including stable part IDs/order, contain-center placement, `paint: none` omission, and point legend swatch parity.
- Snapshot/scenario comparison span and point, including stable source item/projection-instance identities and only the named within-bundle overlays.
- Closed Actual span, Actual point, and open Actual span ending at the explicit selected `as_of`; also missing-Actual treatment and typed absent-cutoff failure.
- Progress fill clipped to its host, with only the progress role's stroke if emitted; verify it does not create an extra item or re-expand the host.
- Attached point mark and its independent required title/date/delta text identity, source port, deterministic order, and host-lane pinning.
- Selected vector icon paths and raster viewport. Preserve normalized path ID/order/cap/join/stroke scaling and asset identity; raster reserves its placed viewport without alpha inspection.
- Stroke conversion: `ObstacleRect` bounds expand by half stroke width; `ObstacleSegment` retains centerline and its one stroke-width carrier; closed/path control-point envelopes expand 10× stroke width per side; clearance is passed separately. Invalid/unsupported/missing geometry never gets dropped or converted to a fit rejection.

## Mapper-to-B2 identity invariant

The immutable `LaneMarkFacet` sequence is the sole source for the facet footprints tested by allocation and the completed geometry, primitive IDs, source references and ports exposed to B2. Projection-instance identity includes View `row_id` plus item ID (or stable automatic projected object instance); source/object `source_ref` is separate. When the same source/object occurs in multiple explicit rows, B2 maps each port/primitive to the exact instance. B2 may apply only the approved shared frame translation and must project the retained path/geometry; it must not rebuild from projection, Theme, icon payload, Scene paint, or a second scale. The mapper's `as_of` must equal the final `PresentationContract.time.as_of`; a mismatch fails before output. These invariants are tested at the seam but B2 realization remains out of this slice.

## Regression, materializers, and release gates

- No Project/View/Actual/Theme/Scene or adapter schema, preset, resource mirror, or generated schema change is intended. If a change becomes necessary, stop and amend design/review/planning first.
- Capture pre-change automatic and explicit Scene and SVG output at this base; compare exact bytes after S2. Include built-in point symbols, multi-part glyphs, point legend variants, vector icons, and material-icons SVG. Any changed bytes need attribution; unexplained output changes block acceptance.
- Render the focused corpus through SVG, PNG, PDF, Typst, and TikZ where supported. Inspect Scene/SVG and raster/PDF/TikZ output as a batch; preserve the established Typst general-path rejection behavior. No adapter geometry repair or Scene paint policy change is allowed.
- Run focused lane allocator, mapper, preflight, Layout geometry, Theme, Scene-ownership, diagnostic-inventory, float-accumulation, and module-reachability checks in the project virtual environment. Do not run a duplicate full local suite.
- At publication, use the repository CI matrix for three-OS full pytest/conformance, wheel/smoke and newest-Python public-materializer evidence. Inspect all checks, generated diffs, and rendered evidence. S2's implementation review records exact commit/commands, every artifact comparison, architecture findings, and all nine literal rows below as `deferred`.
- Do not remove the public lane guard in S2. B2 consumes the frozen plan, B3 follows accepted B2, and L3c owns public activation/resources.

## Literal issue acceptance criteria — all deferred by S2

### #467

- [ ] A lane row mode exists. On `02-programme-board` the 26 items occupy at most 12 lanes, with the chain `structure → avionics → bus-test` on one lane.
- [ ] Every packed task and milestone has a visible name on the slide; no `W_LAYOUT_LABEL_SUPPRESSED` for a packed item on any committed slide.
- [ ] Lane assignment is deterministic, and a test shows that one inserted item does not reorder unrelated lanes.
- [ ] Deltas remain visible for packed items that have them.
- [ ] New Views and the packaged presets default to lanes; `automatic` still renders exactly as today.
- [ ] At least three committed slides use lanes (for example `01`, `02` and `06`), and their evidence is reproducible.

### #494

- [ ] On `02-programme-board` (lanes), no relation is suppressed for `egress-collision`, and every remaining suppression is listed with a measured cause.
- [ ] `test_lane_relation_routes_never_cross_a_required_lane_label` still passes on 02, 11 and 12: no route crosses any lane or member label.
- [ ] Lane count and lane membership on 02 are unchanged, or any change is attributed.
