# Architecture Review — Point Relation Ports (#466)

**Reviewed:** [correction](../../design/issue-466-general-placement-point-relation-port-correction-2026-09-26.md) against Specifications 06, 08, 33, 38, 44 and 50, the annotation-port correction, current mark/route composition, #449 visible fallback and #467 lane packing.

The Project still owns dependency endpoints, while Layout owns their visible port projection. Choosing a finite boundary tip from a completed point glyph is a Layout operation and does not change scheduling semantics. A whole-mark exemption would breach the shared obstacle contract; retaining a center port would cause false route suppression. The correction is compatible with annotation boundary egress and uses the same stable port vocabulary. It does not require Scene or SVG to reroute. Accepted for O2. The public aster-ssd path change and any other point relations require batch Scene/SVG review; no unexplained relation suppression is accepted.
