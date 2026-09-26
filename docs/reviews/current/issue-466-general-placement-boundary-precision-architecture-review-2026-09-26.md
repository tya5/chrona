# Architecture Review — Obstacle Boundary Precision (#466)

**Decision:** approve the [boundary-precision correction](../../design/issue-466-general-placement-boundary-precision-correction-2026-09-26.md) for the shared index used by all Layout placement families.

The Project and View coordinates are unchanged; Layout's typed obstacle geometry owns the contact test; Scene and adapters serialize the completed route without precision-specific repair. The rule is compatible with [Specification 33](../../specification/33-intent-oriented-layout.md), the [shared obstacle model](../../design/issue-466-general-placement-design-2026-09-26.md), the [comparison-egress correction](../../design/issue-466-general-placement-comparison-egress-correction-2026-09-26.md), and the existing `1e-6` visible-rectangle overlap tolerance in `surface_quality.py`. This narrower `1e-9` contact tolerance addresses floating representation noise only; it is not a global collision exemption.

Risk: a short segment inside a mark could be misclassified if the threshold were widened. Focused tests and public controller-z SVG inspection are required. Keep the annotation leader's actual bend/detour profile unchanged and verify the regenerated route is orthogonal rather than a direct diagonal fallback.
