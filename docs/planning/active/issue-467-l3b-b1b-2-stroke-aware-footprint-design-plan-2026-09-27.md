# Design Plan — L3b B1b-2 Stroke-Aware Footprint Seam (#467, #494)

**Baseline:** fetched `origin/main` at `55b38458b96862917f4ad1bb196649ff6d945144` (2026-09-27). **Triggered by:** the B1b-1 atomic bundle allocator review, which leaves the projection-to-bundle mapper as the next isolated seam. **Predecessors:** [candidate-footprint design plan](issue-467-l3b-candidate-footprint-design-plan-2026-09-27.md), [B1b atomic-bundle publication amendment](issue-467-494-l3b-b1b-atomic-bundle-publication-amendment-2026-09-27.md), [candidate-footprint correction](../../design/issue-467-l3b-candidate-footprint-correction-2026-09-27.md), [L3b pre-layout/route-evidence correction](../../design/issue-467-494-l3b-prelayout-route-evidence-correction-2026-09-27.md), and [B1b-1 implementation review](../../reviews/current/issue-467-494-l3b-b1b-atomic-bundle-allocator-implementation-review-2026-09-27.md). This plan is a discovery and planning record only: it selects no footprint semantics, changes no normative contract, and authorizes no product code.

## Published baseline

### Verified published facts

- #467 remains open. Its literal acceptance is six criteria; #494 remains open with three. They are reproduced verbatim below from their GitHub issue bodies as read on 2026-09-27.
- B1b-1 has been published as an allocator extension for immutable atomic bundles. The allocator consumes `LaneMark`/`LaneMember` values containing renderer-neutral `ObstacleGeometry`; the `LaneMark` contract says callers supply stroke-expanded bounds or segments. It does not map `ReviewProjection`, resolve mark roles from render inputs, or establish that supplied footprints match all geometry emitted by final composition.
- The B1b-1 implementation review defers projection mapping, B2 composition/realization, B3 route-cause integration, and public activation. `_project_review` remains fail-closed for lane mode.
- The selected L3b design assigns measurement, mark and label geometry, lane assignment, and routing to Layout. Theme tokens define mark styling, Scene projects completed geometry, and adapters serialize it.
- The published candidate-footprint correction describes the semantic bundle membership and requires the preflight and final composition to use the same Theme mark-role geometry and temporal scale. It requires footprints for planned, comparison, actual, missing-actual, progress, attached-point and selected icon-leading geometry, but its text does not enumerate an exact stroke-expansion rule for each emitted mark primitive.
- The shared obstacle index supports rectangular and segment geometry with stroke/clearance information. Final surface composition reads Theme `strokeWidth` for dependency and leader paths. This establishes a relevant existing mechanism, not yet the exact mark-to-footprint mapping for B1b-2.
- Specification 38 §3.1 and Specification 50 §3 contain the normative lane and route contracts. The B1b-1 review reports its focused allocator and materializer checks, but those do not verify a projection mapper or parity between mapped footprints and final mark strokes.

### Inferences and unverified points

- A footprint mismatch at this seam could allow a mark's visible stroke to overlap a lane label or another mark even when the allocator's geometric body does not. Conversely, over-expanding every shape by one generic amount could create false lane conflicts and alter lane membership. This is an engineering risk inferred from the current separation between allocator input and final mark construction; no mismatch is claimed as measured.
- The exact final primitives and their Theme stroke roles for planned spans/points, scenario/snapshot marks, closed/open/point actuals, missing-actual treatment, progress, and attached points must be inventoried against current composition code before a design choice is made.
- Whether stroke width alone closes each primitive's collision footprint, or whether cap/join/marker geometry and explicit clearance also contribute, is not established by the published B1b-1 contract. Existing `ObstacleSegment` semantics and mark primitive serialization need a direct cross-check.
- It remains unverified whether each role's Theme stroke width is already reflected in an emitted geometry bound, obstacle footprint, or both; which overlay pairs intentionally share geometry; and how those facts should be normalized at the ReviewProjection/Layout boundary.
- Current-main HALCYON lane membership and route output are not evidence for this seam: lane mode remains fail-closed, and the B1b-1 acceptance review expressly did not exercise a mapper or public lane render.

## Objective and boundary

Determine and document a complete, renderer-neutral contract for the **B1b-2 projection-to-bundle footprint mapper**, centered on consistency between each supplied candidate footprint and the mark geometry that final Layout emits. The design work must identify where Theme role metrics, mark geometry, explicit overlays, source identities, and any stroke expansion enter that contract. It must be reviewed against the current Review projection, allocator, obstacle index, composer, Scene request transport, and Specifications 38/50 before any mapper implementation plan is treated as final.

The planned seam starts with selected Review row and attachment/comparison intent, and ends with a complete immutable bundle accepted by the B1b-1 allocator. It includes the semantic-to-geometry mapping questions needed to establish stroke-aware bounds. It does not implement the mapper, wire lane mode into the render pipeline, revise route policy, change View/Project/Actual schemas, activate lane Views, migrate resources, or claim any #467/#494 acceptance row.

## Use cases to resolve

1. A planned span and planned point must be represented in the candidate bundle with footprints consistent with their final Theme roles and emitted mark geometry.
2. Comparison, snapshot/scenario, actual closed/open/point, missing-actual, and progress geometry must be represented or explicitly classified as an intentional overlay/inset without hiding its source identity.
3. An attached point must remain a distinct member pinned to its host bundle and lane, with its own mark and required text footprints.
4. The same semantic member may produce more than one final mark primitive; the mapper must not omit a stroke-bearing primitive or count an intentional duplicate as an unrelated lane candidate.
5. A Theme role or mark kind that cannot be mapped to a closed footprint must have a deterministic, reviewable failure behavior before allocation/output.
6. Existing `automatic` and `explicit` composition must retain its published behavior and bytes while a direct B1b-2 seam is introduced.

## Dependencies and source inventory

Before design selection, inspect and record the current definitions and ownership in:

- `src/chrona/presentation/review/v05_content.py` and the current Review projection/member structures, including #486 attachment intent.
- `src/chrona/presentation/layout/lane_allocation.py` (`LaneMark`, `LaneMember`, `LaneCandidate`, bundle validation, and allocator collision calls).
- `src/chrona/presentation/layout/obstacles.py` (`ObstacleGeometry`, `ObstacleSegment`, `ObstacleRect`, `SurfaceObstacleIndex`, and clearance/collision semantics).
- `src/chrona/presentation/layout/surface_composer.py` and `presentation.py` for final role-specific mark geometry, Theme stroke lookup, mark placement, and obstacle registration.
- Scene request/result types and mark adapters, only to establish what Layout geometry is serialized and whether their primitive shape expands beyond its current layout bounds.
- `docs/specification/38-review-row-composition.md` §3.1, `docs/specification/50-constraint-driven-gantt-surface-quality.md` §3, the B1b-1 review and B1b publication amendment, plus #486 and the accepted #466 route-priority contract.

Published constraints to preserve during the design: Layout owns measurement and completed geometry; candidate identity and per-member source identity stay separate from generated lane identity; explicitly allowed overlays are narrowly scoped and never exempt required text; routes may not cross required labels; the public lane guard stays closed until later approved slices; and the `automatic`/`explicit` path remains byte-characterized.

## Design questions — unresolved

1. What exact final mark primitive inventory and geometry constructor is authoritative for each semantic mark role, and how does each map to one or more obstacle shapes?
2. For each primitive, what is the authoritative stroke width and coordinate transform at the mapper boundary? Is stroke expansion performed by the geometry constructor, the obstacle geometry, or a distinct adapter from rendered style to obstacle extent? How is double expansion prevented?
3. Which cap, join, marker, outline, and endpoint details change the visible footprint beyond a simple stroke-expanded rectangle/segment? Which can be represented exactly by existing `ObstacleGeometry`, and where would an explicit conservative envelope be necessary?
4. How does the contract distinguish visible stroke extent from collision clearance? Are they separately recorded, and what existing `SurfaceObstacleIndex` rule governs each?
5. Which Theme style roles may be absent, inherited, or unresolved at preflight? What typed failure is appropriate when a required stroke metric or mark shape is unavailable, and at what layer is it raised?
6. How are compound/faceted marks (planned plus progress; actual plus point glyph; comparison overlays) represented without losing primitive identity or applying the same stroke more than once? Which overlap declarations remain valid under stroke-aware bounds?
7. What numerical precision/tolerance contract makes footprint collision outcomes deterministic across preflight, final composition, and materializers?
8. Which neutral fixtures can establish role-by-role parity without importing Project/View/Scene concerns into the allocator? Which integration fixture is needed later to prove the mapper receives complete selected row facts?
9. Does closing the discovered contract require a normative Specification 38 and/or 50 amendment, or can existing language already express the selected geometry rule? This must be answered by the design/review, not presumed here.

## Planned design slices and evidence

| Slice | Work and owners | Evidence and exit condition | Publication boundary |
| --- | --- | --- | --- |
| **D0 — baseline inventory** | Read the current projection, mark constructors, Theme role metrics, obstacle geometry and emitted Scene primitives. Trace each mark role end-to-end and document the published, inferred and unverified facts. | A role-to-source-to-Layout-geometry-to-Scene-primitive inventory; explicit list of stroke/cap/join/marker and clearance questions; no changed behavior assumed. | This plan is the D0 output. Any inventory correction belongs in a successor design correction, not silently in code. |
| **D1 — footprint contract design** | Specify mapper inputs/outputs, identity, geometry representation, role-specific stroke treatment, clearance separation, overlay validation, precision, and typed failure behavior. Check the result against B1b-1 allocator and current final composer responsibilities. | Every emitted candidate mark primitive has a defined source and footprint transformation; a proof/fixture strategy demonstrates no omission or double expansion; unsupported geometry has explicit behavior; no View or Scene policy is introduced. | Publish a dated design correction and update Specification 38 and/or 50 if normative semantics change. |
| **D2 — architecture review** | Review whole path across projection, View/Review semantics, Theme, Layout, Scene, adapters, #486 attachment, #466 obstacles/routes, and #480/#481 row composition. | Explicit consistency table, alternatives, migration/compatibility impact, unresolved items, and decision on exact B1b-2 seam. | Publish architecture review before implementation planning is finalized. |
| **D3 — implementation plan amendment** | Name exact mapper/geometry files, owner boundary, neutral and integration fixtures, failure tests, generated evidence, automatic-byte characterization, and any module reachability staging/removal. | Independently reviewable B1b-2 slice; direct seam tests for stroke-aware role geometry and identity; mapper-to-allocator tests for bundle closure; all acceptance claims explicitly deferred unless independently evidenced. | Publish implementation-plan amendment before product code. |

## Acceptance evidence required from a later B1b-2 implementation

- Direct role-by-role tests compare mapper footprints with the final Layout mark geometry, covering all inventory rows and showing stroke/clearance applied exactly once.
- Tests cover segment endpoints, point glyph extents, open/closed actuals, progress insets, comparison overlays, attachment pinning, and invalid/missing Theme geometry according to the approved design.
- Bundle identity remains stable and each source mark/text member maps once; intentional overlays are explicit and do not relax label collision checks.
- No Project/View/Scene dependency is introduced into the neutral allocator; Layout remains sole geometry owner.
- Existing automatic/explicit output is byte-characterized, and the public lane-mode guard remains in place.
- Focused tests and static/module reachability evidence run as specified by the eventual implementation plan. Materializers are checked for unintended output changes; no public lane acceptance is inferred from a direct seam test.

## Literal acceptance retained

The following are copied verbatim from the current GitHub issue bodies. They are issue-level acceptance criteria, not completion claims for this design-plan task.

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

## Successor records and publication boundary

On D1 completion, create an issue/topic/date-named design correction linked to this plan; at design completion, publish its architecture review and any normative specification update. Then publish the B1b-2 implementation amendment with exact source files, focused fixtures, no-change characterization, and evidence gates. The B1b-2 implementation may only publish as a partial direct seam; B2 composition/one-plan realization and B3 route-cause integration remain later slices, and L3c alone owns public activation. All nine issue criteria remain open until directly supported by later acceptance evidence.
