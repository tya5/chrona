# Architecture review — `fill`-only lane search (#504)

Reviewed the [correction](../../design/issue-504-fill-only-label-search-correction-2026-09-29.md) against Specifications 38/50, the [stagger-envelope review](issue-504-lane-stagger-envelope-architecture-review-2026-09-29.md), and published R4 label policy. `rowDistribution` is a Layout Profile allocation choice, so it is the correct boundary for the new search/minimum. Layout still owns both candidate geometry and suppression evidence. No View, Scene, or adapter branch is added.

Keeping `pack` stable protects the separate Editorial lane gallery from route-quality regressions while `fill` supplies #504's growth behavior. Acceptance requires 02/11/12 zero suppressions, exact unchanged bytes for every other public slide, focused `pack`/`fill` tests, and CI. Approved for the R2 implementation amendment.
