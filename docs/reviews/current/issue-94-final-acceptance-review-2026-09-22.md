# Issue 94 — Final Acceptance Review

**Reviewed release base:** P94-3 `2c890a4`, P94-4 `934bac9`, P94-5 `f87c56a`.

## Acceptance matrix

| Phase | Requirement | Evidence | Result |
| --- | --- | --- | --- |
| P94-1/2 | Remove unreferenced presentation code and prevent new orphans | #96; CI reachability lint | Pass |
| P94-3 | Decide the test-only modules without false product wiring | #102 removes 19 modules/tests; lint reports 46 reachable, 0 staged | Pass |
| P94-4 | One version identity per resource contract | #107 schemas, closure, examples, and materializer use kind-specific identities; v0.2 Context retired | Pass |
| P94-5 | Reject incomplete surface content at construction | #109 removes every `SurfaceContentInput` default; normalizer and explicit test fixtures supply all fields | Pass |
| P94-6 | One normative Layout → Scene → renderer seam | Specification 08 §2.2; ADR-0031 and Specification 50 | Pass |

## Verification

The final implementation candidates each passed conformance, the full pytest
suite (`214 passed, 4 skipped, 14 xfailed`), the module reachability lint, and
all five public materializer byte checks. No P94-3 through P94-5 implementation
introduced generated SVG differences. The seven warnings are existing
`jsonschema.RefResolver` deprecations.

## Architecture review

The surviving product path is explicit: normalized authoring inputs → Layout
placements → Scene primitives → SVG/PNG serialization. Layout owns all measured
geometry and feasibility; Scene has no font-metric or routing fallback; adapters
cannot reconstruct policy. The repository no longer treats test reachability,
shared version labels, defaulted content, or stale successor release evidence as
evidence of a delivered product path.

## Disposition

Issue #94 is accepted and may be closed after this review and the Specification
08 seam amendment are merged.
