# Issue 85 — Surface Quality Release Review

**Reviewed baseline:** `ef69f5c`  
**Design authority:** `issue-85-surface-quality-remediation-design-review-2026-09-22.md`

## Result

Issue #85 satisfies its approved release gate.  The delivered slices preserve
the architecture boundary: normalization owns display facts, Layout owns
placement and density, Scene projects completed placements, Theme declares
paint/form intent, and SVG serializes that intent without selecting semantics.

## Acceptance evidence

- Actual absence and compact date range values are normalized before Layout.
- Every accepted plot label and standalone delta is bounded and clear of marks.
- Table allocation reserves the declared positive gutter and diagnoses infeasible
  required content.
- Required legend slots have bound profile content; optional notes are not
  treated as missing output.
- Narrow calendar density retains explicitly declared exception closures.
- SVG serializes declared outline and diagonal-hatch forms; print distinguishes
  planned, actual, and missing-actual marks without renderer-side role policy.
- The generated-output property gate has no Issue #85 failure pins.

## Structural review

Scene remains free of direct font measurement and route selection.  Module
reachability and import-direction checks pass.  The five public materializers
were regenerated at each affected slice; the final changed monochrome outputs
were raster-inspected.

## Verification

- focused output-property gate: `21 passed, 4 skipped`
- full pytest: completed after C85-4 merge
- public CI: Ubuntu and macOS conformance succeeded for PRs #158–#161

## Decision

Close Issue #85.  No unresolved Issue #85 output-property pin remains.
