# M27 Presentation Product-Path Implementation Plan — 2026-09-21

**Status:** Authorized by the D27-5 design closure review.
**Design inputs:** ADR-0028, Specifications 08/24/30/33/36, D27-4 acceptance design,
and `m27-presentation-product-path-design-closure-review-2026-09-21.md`.

## Delivery order

| Slice | Scope | Required evidence before completion | Publish boundary |
|---|---|---|---|
| I27-1 | Establish the public completed-Scene composition seam: resolved Detail/Summary/SurfaceContent input, Layout Manifest consumption, and test instrumentation that forbids the reduced path | A27-08 negative reachability; normalized missing values; malformed resolved input rejects before SVG | composition boundary/tests |
| I27-2 | Build core completed Scene families: role typography, title/subtitle, table, natural calendar axis bands/ticks/labels, planned/Actual/milestone/variance/missing-Actual marks | A27-02–A27-04; bounds/collision/overflow tests; no literal stride/defaults | core Scene families |
| I27-3 | Build optional complete families: groups/row shading, finite dependency and annotation routing, legend/coverage, notes/detail/observations/milestones/summary | A27-01, A27-05, A27-06; provenance, capability, and required-slot diagnostics | optional Scene families |
| I27-4 | Switch `render-review` to the completed SceneSurface SVG path and retire public reduced-path reachability | CLI integration, no `table_timeline` product import, retained Context/Color Scheme/Layout behavior | product-path switch |
| I27-5 | Deliver the generic manifest materializer and canonical example reproduction checks; regenerate declared artifacts only from it | A27-07/A27-09; changed artifact detection; every declared slide checks through CLI | materializer and artifacts |
| I27-6 | Register M27 conformance, execute full regression, publish final acceptance review, and close only evidenced Issues | A27-01–A27-10, full pytest/conformance/CI evidence, catalog/ledger consistency | final acceptance |

## Slice rules

1. Each slice starts by adding or enabling its failing automated evidence, then adds
   generic implementation. Tests must not call a renderer-private shortcut to establish
   product acceptance.
2. Publish the complete slice to `main` before beginning the next slice. Run the full
   inherited test/conformance suite at every publish boundary.
3. Preserve immutable Context resolution, source provenance, semantic facets, and the
   Color Scheme boundary. A visual improvement that loses any of those is rejected.
4. Do not regenerate an expected example artifact until the generic materializer and
   its `--check` behavior exist. Do not close #29–#33 early.
5. Any need for an undeclared authoring field, runtime default, parallel renderer, or
   new output target is a design stop: amend D27 design documents, re-review, publish,
   then resume from the affected slice.

## Completion gate

M27 is complete only when the reduced product path is unreachable, all A27 cases have
automated evidence, all declared example artifacts reproduce through the public CLI,
full conformance passes, and the final review ties each closed issue to its acceptance
proof. Until then the M27 roadmap entry remains implementation in progress.
