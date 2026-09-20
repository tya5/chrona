# G1–G4 Integration Remediation Plan

Status: Complete. D0–D3, I1–I3, and V1 acceptance are implemented and validated.
Original review target revision: `82e59f6e13fde8f6582f538da24b7523854c2cde`.
Basis: [cross-cutting review](../reviews/g1-g4-integration-audit-2026-09-20.md).
This document corrects the former G1–G4 completion judgment; it is not a feature
expansion plan.

## Principles

Complete, validate, and publish every design correction before implementation. Branches
on sample names are prohibited. Reuse existing pure functions and split large renderers
into small pure operations. Preserve public API compatibility at entry adapters. Do not
change Core, Store, or Command semantics. Approval of this plan does not mean
implementation is complete.

## Priority and dependencies

| Order | Phase | Scope | Deliverable / exit condition |
|---|---|---|---|
| 1 | D0 completion correction | R01–R04 | Withdraw completion in plans/reviews, register reproductions, fix target SHA, record the failed validator's cause |
| 2 | D1 complete boundary design | R01, R06, R11, R12 | Unify dependencies and responsibilities across Specifications 08/09/29/30/31; define semantic facet, visual role, slot instance, and Scene identity |
| 3 | D2 complete algorithm design | R04–R10 | Fix purpose-specific annotations, port exceptions, occupancy, lane pitch, row correspondence, axis bands, metrics, routing diagnostics, and finite termination |
| 4 | D3 design synchronization and cross-validation | All | Align owner schemas, wire schema, positive/negative fixtures, migration, acceptance table, and review; update base-hash references; approve/publish with zero open design decisions |
| 5 | I1 common Scene construction | R01, R06, R08, R09, R11 | Generate measured Text/Rect/Symbol/Path while preserving semantic marks, with viewport, manifest, and provenance |
| 6 | I2 placement, lane, and routing connection | R02, R04, R05, R07, R10 | Apply independent-lane height/offset to the final Scene; move annotation purpose, ports, and routes to common implementations |
| 7 | I3 public-adapter migration | R01, R02, R06, R08, R09, R12 | Gantt/review/minimal draw one Scene; remove private date, placement, and wording calculation; isolate legacy |
| 8 | V1 acceptance and completion review | All | Pass structural, behavioral, image, and invariant checks; only then restore completion with implementation evidence |

Do not begin I1 until D0→D1→D2→D3 is complete. Review and publish target-only diffs
after every phase. If implementation exposes an undesigned issue, do not patch it
locally: close the full affected design set before resuming.

## D0 execution record

The target revision is fixed at `82e59f6e13fde8f6582f538da24b7523854c2cde`.
R01–R04 in this plan and the integration audit withdraw the former G1–G4 completion
statement. Reproduce at that revision with
`PYTHONPATH=src python timeline-design/docs/fixtures/validate_presentation_g2_g4_design.py`.
The validator alone still expected the removed diagnostic
`E_PRESENTATION_STACK_SURFACE_INCOMPATIBLE`, causing an AssertionError at line 23.
The expectation was synchronized with the current fixture instead of fabricating the
diagnostic again. This synchronization is not the full R03 correction; G1–G4 remains
incomplete until D1–D3 close the owner schemas, wire schema, fixtures, and evidence.

## D1/D2 execution record

D1 fixes `ResolvedPresentationInput`, separation of semantic facet from visual role,
slot-bearing projection instances, Scene identity, and non-reinterpretation by adapters
across Specifications 08/09/29/30/31. D2 makes Specification 30 §7.5 the sole finite
projection procedure and fixes one-time TextLayout measurement, purpose-specific
primitives, shape-derived ports, the lane formula, and separate route-limit versus
unroutable diagnostics. D3 synchronizes these rules into schemas, fixtures, acceptance
tables, and validators. I1 does not start before D3 completes.

## D3 execution record

The wire-routing input closes over `gridOffset`, `clearance`, `portOffset`,
`bendPenalty`, and `limit`, verified by positive/negative fixtures and a validator.
`row-aligned` no longer requires stack zero; it retains `stackIndex` as Scene metadata.
No inconsistency may remain among the D1/D2 boundary, finite procedure, owner schemas,
wire schema, and fixtures. I1's first acceptance condition is a completed Scene from
Specifications 08/30 `ResolvedPresentationInput` with no adapter reinterpretation of
meaning or geometry.

## Design correction when starting I3

Adapter-migration inspection found that adapters would recalculate coordinates unless
resolved bounds for surface slots, rows, and lane tracks were explicit Scene inputs.
Specifications 08/30 were corrected, and I3 paused until those inputs moved into the
Scene Builder. Published I1/I2 primitive/track work is an intermediate foundation, not
evidence of I3 completion.

## Second I3 design correction: public surface instances

After row/group migration in the table/timeline adapter, the regular review and minimal
SVG adapters were found to reconstruct date-to-X and item-to-Y from settings margins,
day width, row height, and projection order. This violates Specification 08's adapter
prohibitions and I3's all-public-path condition. `table-timeline`, `review`, and
`minimal` are therefore independent surface instances in ResolvedPresentationInput.
The Scene Builder fixes each instance's title/timeline/axis/ordered-row bounds and
completed primitives. A common `scaleId` shares only normalized positions, never
origin, width, day width, or row height. Missing surface input or primitives diagnose;
the adapter does not calculate a fallback. Publish specification, derived fixture, and
validator corrections before resuming review/minimal migration.

## Closure of completed primitives and adapter migration in I3

I3 is not complete when Scene-derived metadata merely exists. On every public surface,
the adapter must stop reconstructing date→X, row→Y, axis band/ticks, marks, Text,
connectors, annotations, and table/legend/summary geometry. The implementation order,
primitive families, remaining scope, and publication boundaries are owned by
`i3-surface-adapter-completion-plan-2026-09-20.md`.

I3-A design closure requires completed title, axis-band, axis-label, tick,
comparison-mark, and item-label primitives on each surface; ownership by
`SceneSurface`; primitive identity; Text payload/baseline; and
`E_PRESENTATION_SURFACE_MISSING` / `E_PRESENTATION_PRIMITIVE_MISSING`. This is an
implementation prerequisite and MUST NOT be reinterpreted by I3-A-or-later adapters.

## Proposed internal structure

1. Input resolution: validate typed/fixed references for View, Style, Theme, Detail,
   Layout, and Context; select sources once.
2. Semantic projection: preserve semantic facets and observations; keep baseline and
   other visual presentations as separate attributes.
3. Measurement: consume role, family, weight, locale, and fixed assets; produce
   TextLayout with bounds, baseline, lines, and selected asset.
4. Geometry placement: resolve scale, axis bands, item rows/lanes, labels, and
   annotations with finite procedures.
5. Routing: search finitely from measured obstacles and shape ports; separate meanings
   of dependency, leader, and explanatory arrow by policy.
6. Scene finalization: immutably retain primitives, stable identity, `sourceKind`,
   bounds, z-order, manifest, and diagnostics.
7. Output: serialize primitives to SVG or another target; prohibit date calculation,
   anchor selection, remeasurement, and replacement.

Do not keep `scene.py` and `presentation_scene.py` in unexplained parallel roles.
Distinguish semantic input DTO from geometric Scene in names and types. Add no
persistent authoring format; typed internal DTOs are derived data, not a second
Schedule source of truth.

## Required acceptance cases

| Class | Case | Pass condition |
|---|---|---|
| G1 axis | Quarter/month/week/day, clipping, ISO-year boundary, multiple slots | All declared labels/bands render and positions agree on the shared scale |
| G1 comparison | Point Actual, one missing endpoint, baseline plus planned annotation | Do not discard or complete Actual; display mode does not change anchor identity |
| G2 measurement | Bold, Japanese, letter spacing, long text, changed `maxCandidates` | Drawing and collision use one TextLayout; search count follows the contract |
| G3 purpose | Note/callout/highlight/two-endpoint arrow/no leader | Primitive composition, `sourceKind`, and references match each purpose |
| G3 port | Body/start/finish/point, multiple slots, separate marks at same coordinates | Exclusion uses source ID; only the first exit segment may cross an obstacle interior |
| G4 | Overlapping planned/actual/required labels, point symbols, group order | Stack from measured geometry; insufficient track height diagnoses; no group moves |
| G4 output | Switch one projection between row-aligned and independent lane | SVG Y coordinates and track backgrounds change as designed; metadata-only differences do not pass |
| All paths | Gantt/review/minimal and setting mutations | Supported settings affect output or explicitly diagnose unsupported; no silent ignore |
| Reactive | Same source in multiple slots; one object update | No `sceneId` collision and no required full regeneration of unrelated scopes |
| Validation | All design validators, unit/integration tests, and images | Include validators in normal CI; verify semantic values, source IDs, and bounds before golden update |

## Final completion conditions

- Map every acceptance case to a specification section, schema path, implementation
  symbol, test, and output artifact.
- Use sample-independent cases in addition to ASTER/Controller Z; confirm immutable
  input Project/Schedule/Actual.
- Preserve image diffs for human review; regenerating goldens alone does not pass.
- Mark each setting consumed or explicitly unsupported; do not complete unconsumed
  settings.
- Separate design and implementation reviews; publish fixed evidence, target revision,
  and remaining scope.

This plan excludes a complete rewrite, free-coordinate DSL, per-sample renderer,
arbitrary extension framework, and new temporal model. Estimate precisely only after
D3 closes the change surface. The main current risk is API and golden-output churn
while ownership moves into Scene.

## Final execution record

The corrective sequence completed without widening the exclusions above. Design parent
`666007acac8602350db5cbb633c017b35a0d7d2b` closes the last manifest shape;
manifest implementation `b32b1237ee60a0da892372acc150009dc69c91b0` completes the
Scene DTO, all three adapter surfaces, target metadata, Japanese/long-text behavior,
and initial inspection SVGs. Contrast implementation
`45fda25b380b8333aadadd5706c2ba6364758d3a` corrects the post-acceptance invisible
axis/table labels and regenerates the reviewed output set. The final acceptance review
records the exact evidence map and image hashes. The full 179-test suite and the complete conformance runner pass;
only two pre-existing `jsonschema.RefResolver` deprecation warnings remain. R01–R12 and
all D0–D3/I1–I3/V1 work in this remediation plan are closed.
