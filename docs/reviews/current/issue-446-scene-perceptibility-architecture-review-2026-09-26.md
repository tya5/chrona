# Architecture Review — Serialized Scene Perceptibility Gate (#446)

**Design under review:**
`issue-446-scene-perceptibility-design-2026-09-26.md`.
**Decision:** Accepted for implementation planning; implementation remains
gated on the P0 release review and current CI result.

## Boundary review

| Boundary | Result | Guardrail |
| --- | --- | --- |
| Layout → Scene | Pass | The evaluator observes completed geometry/order/paint/slots.  It cannot measure, wrap, route, select a fallback, or revise a placement. |
| Scene → adapters | Pass | The adapter remains a serializer; no raster comparison, SVG-specific ordering rule, or post-render correction enters the evaluator. |
| typed host relation | Pass | Only an already validated same-surface `hostPlacementId` classifies an intended text/host relation.  Geometry and primitive IDs cannot form an allowlist. |
| #449 overflow | Pass | `visible-overflow` is observed as an individually identified declared outcome; it is not transformed into an error, silent exemption, or a count baseline. |
| #445/#455 completion | Pass | Slot errors are evaluated after completed Layout geometry.  The tool cannot excuse an unpermitted escape or repair a footer allocation. |
| #431 contrast | Pass | #446 supplies only compositing facts.  Role classes, floors, and palette migration remain a separate policy decision. |
| draft feedback | Pass | Warnings derive from a post-Scene evaluation and retain the successful artifact.  They do not alter immutable bytes. |
| CI orchestration | Pass | One named conformance gate consumes committed Scene files; it neither invokes full pytest nor changes matrix cancellation/reporting, which #451 owns. |

## Required corrections before implementation

1. The implementation plan must define one shared transport form for the pure
   evaluator so direct Scene mappings, file tool input, and draft Scene output
   cannot drift.  Do not create separate tool and runtime algorithms.
2. The tool report must make informational declared-overflow findings visible
   without treating them as a passing count baseline.  New input is always
   reclassified by policy and facts.
3. The draft diagnostic mapping must preserve the original finding identity
   and measured facts in a stable machine-readable result, not only in prose.
4. The P0 acceptance review must record the zero-error prototype against the
   corrected `#443/#455` evidence before implementation.  If CI or that review
   exposes a P0 regression, return to its owning design rather than adding an
   evaluator exception.

## Conclusion

The design maintains the intended ownership model and creates a reusable,
renderer-neutral observation seam.  It is authorized for implementation
planning only.  Source changes wait for the P0 gate, avoiding the circular
practice of treating a prospective checker as acceptance for known defects.
