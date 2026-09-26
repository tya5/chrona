# Architecture Review — Coherent Allocation and Starter Gate (#468)

**Design:** [issue-468 design](../../design/issue-468-coherent-draft-allocation-design-2026-09-26.md).
**Published base:** `f1369594cc7343fbde789d2f533255fd323ace8c`.

The problem is a split Layout decision, not a Scene or adapter rendering
defect. `render_review` already asks Layout for the timeline's content extent
but ignores that answer on fixed requests; later surface composition grows
only the canvas. Re-solving the profile before surface placement restores
normal-flow ownership: table/timeline/review-surface share a host, and notes
follow it. A Scene-side note offset or warning suppression would leave the
profile internally contradictory and is rejected.

The design was checked against Specifications 33, 08 and 50, ADR-0031, #365
Draft auto, #449 visible completion and #446 perceptibility. The requested
viewport remains a minimum as #449 already states; the new rule narrows when
Layout must extend allocation **before** falling back to canvas-only growth.
The pure #446 evaluator remains the sole text-intersection algorithm; its
starter input is an additional product render, not an exception list. View
owns declared axis intent, Layout fits and places it, Scene projects it, and
adapters serialize it. Changing the packaged default View does not expand
the View schema or mutate independent user Views.

Decision: accepted. Residual risk is that a profile's fixed/max constraints
may prevent the timeline source from receiving added block space. The Layout
resolver must detect this deterministically and use #449's visible fallback
only for true structural non-growth, not pretend its host grew. Public byte
changes and migration will be checked in the implementation plan.
