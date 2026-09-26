# Implementation Amendment — Boundary Precision (#466)

**Amends:** [O2 prerequisite plan](issue-466-shared-obstacle-prerequisite-implementation-plan-2026-09-26.md) after the [design correction](../../design/issue-466-general-placement-boundary-precision-correction-2026-09-26.md) and [architecture review](../../reviews/current/issue-466-general-placement-boundary-precision-architecture-review-2026-09-26.md).

Update only the shared segment/rectangle interior predicate in `obstacles.py` with the specified contact tolerance; do not special-case controller-z or raise router limits. Add exact/noisy boundary and real-crossing tests in `test_obstacles.py`. Re-run controller-z annotations integration, inspect the SVG route geometry, then regenerate/check all public artifacts and diagnostic inventory as part of O2 acceptance.
