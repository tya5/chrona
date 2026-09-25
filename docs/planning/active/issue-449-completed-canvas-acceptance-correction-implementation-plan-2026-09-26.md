# Implementation Plan — Completed-Canvas Acceptance Correction (#449)

**Design:** `issue-449-completed-canvas-acceptance-correction-2026-09-26.md`  
**Architecture review:**
`issue-449-completed-canvas-acceptance-architecture-review-2026-09-26.md`

## I449-AC-1 — Parse the published canvas

In `tests/acceptance/output/test_generated_output_properties.py`, add a small
SVG-root helper that returns the validated completed dimensions.  It must parse
numeric root width/height and the four `viewBox` values, reject non-zero origin
and inconsistent values, and assert that both completed dimensions are at
least the Context request.  Keep this helper local to output-property testing;
it is not product geometry.

**Acceptance:** focused unit-style test cases cover request-size, expanded,
incoherent, translated, and undersized root canvas values.

## I449-AC-2 — Check text against the completed canvas

Replace the stale requested-viewport containment boundary with the parsed SVG
boundary.  Keep the diagnostic fingerprint and the existing known-failures
protocol unchanged.  Do not pin the Controller-Z failures and do not modify
generated artifacts merely to satisfy the old assertion.

**Acceptance:** every committed output property passes; Controller-Z’s seven
former false failures produce no known-failure entries.

## I449-AC-3 — Verify the release evidence

Run the focused acceptance module and public materializer reproduction.  Inspect
the completed SVG root dimensions for a normal and an expanded Context.  Push
the implementation only after a clean diff and remote-main freshness check;
then use one three-platform CI result as the full-suite release gate.
