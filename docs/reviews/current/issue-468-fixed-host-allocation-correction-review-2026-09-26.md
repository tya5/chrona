# Architecture Review — Fixed-Host Allocation Correction (#468)

**Correction:** [fixed-host design](../../design/issue-468-fixed-host-allocation-correction-2026-09-26.md).

The correction restores the distinction already present in Specification 33:
a growable profile should reallocate its normal-flow host, while a fixed or
capped host may only expose a truthful visible fallback. The proposed
candidate must be validated against actual LayoutManifest decisions; a
caller-side guess from canvas size is not evidence. Scene and adapters remain
unchanged, and the #446 evaluator still reports any resulting text overlap.
No source identity, View syntax or arbitrary HALCYON branch is added.

The two observed public artifacts are regression fixtures for the no-op
case. Their original Scene/SVG bytes should remain unchanged; the default
growable Draft must still expand table/timeline/review-surface and move notes.
The whole architecture remains consistent with #365 auto, #449 visible
fallback, Specifications 08/33/50 and ADR-0031. Decision: accepted before
resuming I468-1 code.
