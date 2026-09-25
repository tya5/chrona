# Architecture Review — P0, P1, and P2 Remediation (#454)

**Design reviewed:**
`issue-454-p0-p1-p2-remediation-architecture-design-2026-09-26.md`.
**Decision:** accepted for per-slice implementation planning.

## Boundary review

| Boundary | Required ownership | Review result |
| --- | --- | --- |
| View/Theme → Layout | Finite boolean presentation, typography, overflow, and color intent. | Accepted; no target formatting or hidden boolean coercion. |
| Layout → Scene | Completed line geometry, host relation, canvas, warning, and resolved paint order. | Accepted; the Scene receives facts rather than a request to resolve paint order. |
| Scene → adapter | Stable primitive serialization in supplied order only. | Accepted; no SVG loop-order repair or font/geometry fallback. |
| Scene → quality tool | Observation of public completed facts. | Accepted; findings cannot mutate the artifact or replace Layout validity. |
| Closure → draft renderer | Exact selected face catalog and registered draft files. | Accepted; multi-face support cannot weaken the no-fallback resource rule. |
| Init/docs → corpus evidence | Editable source, hidden closure, and manifest-generated evidence have separate ownership. | Accepted; an image reference is verified evidence, not a copied presentation file. |

## Findings and required controls

1. **Host relation must be validated, not merely serialized.**  A
   `hostPlacementId` must name a completed primitive in the same surface and
   be compatible with the text semantic category.  An arbitrary string would
   turn the #446 intended-overlap exception into an unbounded allowlist.
2. **Paint strata are an ordering relation, not a replacement for semantic
   roles.**  Existing semantic ids continue to select paint; strata only
   resolve their relative order.  A new visual treatment cannot be encoded by
   assigning an arbitrary number in a Scene builder.
3. **Rotated lane allocation precedes collision checking.**  A single domain
   alone would make #443 fail more often without reserving space.  The
   implementation plan must require transformed lane measurement first, then
   use cross-tier collision as a negative guard.
4. **Wrapped panel height affects completed canvas through Layout.**  No P0
   implementation may clip, resize, or line-break detail text in a target.
   The existing #449 visible-overflow completion and warning closure is the
   only fit fallback.
5. **Scene perceptibility and contrast have distinct scopes.**  #446 owns
   common geometry/paint collection and finding protocol; #431 owns role
   classification, thresholds, theme migration, and release report.  Their
   implementation must share a small pure evaluator instead of duplicating
   contrast calculations.
6. **Aggregate diagnostics require independence classification.**  A semantic
   check dependent on an invalid schema value is skipped with a recorded
   reason, not run against malformed data.  Independent resources and checks
   still accumulate deterministically.
7. **The #448 audit narrows, but does not close, the issue.**  Exact catalog
   selection resolves immutable bold measurement.  The draft multi-weight
   request remains a real closure concern and needs its own focused acceptance
   evidence before the issue can close.
8. **#378 is not permission to grow guided authoring.**  The later
   inheritance/rung decision is explicitly deferred to a bounded design if
   current preset and minimal-init mechanisms cannot meet the literal ladder.

## Whole-architecture consistency

The design agrees with the released #449 rule: fit/placement failure is
completed visibly and recorded, while malformed input and missing resources
remain errors.  It agrees with #410's measurement rule: Layout selects exact
font bytes before every measurement.  It preserves the repository's typed
contract direction and avoids parallel scene/render models.

P0 must publish before #446 because a gate that accepts the known broken
corpus would institutionalize the defects it is intended to prevent.  #441
must follow #439 because the README hero must become a currently generated,
legible artifact.  The remaining P1 feedback work may be independently
planned after this review; publication remains serial.

## Required evidence for implementation planning

- P0 negative and positive Layout/Scene fixtures for host validation,
  cross-tier rotation, boolean format validation, and wrapped panels.
- Regenerated public artifact evidence plus Scene-level assertions that the
  formerly hidden/overprinted content is visible and ordered correctly.
- A before/after empty-baseline run of the #446 evaluator, with no numeric
  blanket suppression.
- Deterministic result fixtures for CI aggregation and presentation diagnostic
  aggregation.
- Public materializer, generated-document, conformance, wheel, and
  three-platform verification in release slices; local work remains focused
  rather than duplicating the remote full suite.
