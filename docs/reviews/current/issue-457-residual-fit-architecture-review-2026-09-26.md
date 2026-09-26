# Architecture Review — Residual Fit Closure (#457)

**Decision:** approve the [residual-fit correction](../../design/issue-457-residual-fit-correction-2026-09-26.md) before L2 code.

| Boundary | Finding |
| --- | --- |
| Theme/View to Layout | Exact visual size and explicit overflow intent arrive as input; an invalid ratio diagnoses there, while an insufficient slot is a placement fact. |
| Layout | One measured visual-plus-text run owns natural fallback, warning extents, and both-sided completed canvas. |
| Scene and adapters | They only project placements and canvas; no renderer-local clip, scale, or reroute can hide the shortage. |
| Immutable/Draft | Both paths use the same Layout closure, so tests must exercise both. |
| Adjacent fit designs | #449's visible fallback and Specification 50's measured text rules remain intact; no compat branch or new schema is required. |

Review risks: icon/text baseline alignment and negative-origin SVG viewBox.
L2 tests must inspect the actual rendered artifact, not only a Scene record.
