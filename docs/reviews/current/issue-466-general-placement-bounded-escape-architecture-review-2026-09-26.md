# Architecture Review — Bounded Perimeter Escape (#466)

**Decision:** approve the [bounded escape correction](../../design/issue-466-general-placement-bounded-escape-correction-2026-09-26.md) after the ordinary shortest-grid search, without raising its state limit.

The candidate family is geometry-only and computed inside Layout from the same typed obstacle inventory. Project/Review relation semantics, View endpoints, Theme paint, Scene projection, and adapter serialization do not change. It respects [Specification 33](../../specification/33-intent-oriented-layout.md), the [shared-obstacle design](../../design/issue-466-general-placement-design-2026-09-26.md), and the [boundary-port and comparison-egress corrections](../../design/issue-466-general-placement-comparison-egress-correction-2026-09-26.md). Every escape segment is collision-checked and callers still enforce their declared profile quality.

Risk: an envelope route may be visually long or exit the useful drawing region. Tests must prove the candidate cap, bounds rejection, obstacle avoidance, stable selection and unchanged ordinary route results. Inspect controller-z annotation SVG and public route-fallback changes; a path may be accepted only if it remains within the existing explicit quality policy.
