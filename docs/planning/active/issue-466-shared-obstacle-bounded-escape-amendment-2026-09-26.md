# Implementation Amendment — Bounded Perimeter Escape (#466)

**Superseded:** the [rendered non-acceptance review](../../reviews/current/issue-466-bounded-escape-nonacceptance-review-2026-09-26.md) rejects this implementation route. O2 remains paused pending the [topology design plan](issue-466-annotation-route-topology-design-plan-2026-09-26.md).

**Amends:** [O2 prerequisite plan](issue-466-shared-obstacle-prerequisite-implementation-plan-2026-09-26.md) after the [design](../../design/issue-466-general-placement-bounded-escape-correction-2026-09-26.md) and [architecture review](../../reviews/current/issue-466-general-placement-bounded-escape-architecture-review-2026-09-26.md).

Implement the at-most-eight perimeter candidates in `routing.py` only after the existing bounded A* cannot complete. Reuse its exact segment collision query, port exemptions, selected classes/regions and route bounds. Add focused dense-grid, no-path and bounds tests. Keep `limit=1024` for annotation leaders and all layout-profile quality thresholds. Regenerate controller-z annotations, require the leader test to pass without direct fallback, inspect SVG, then batch-check public artifacts and CI before O2 acceptance.
