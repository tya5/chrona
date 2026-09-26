# Architecture review — as-of label placement (#458)

**Design:** [#458 design](../../design/issue-458-as-of-label-suppression-design-2026-09-26.md).

Accepted. Specification 50 gives Layout complete geometry and permits visible
fallback; the current hard-coded as-of suppression violates that principle.
Specification 08 and #446 keep Scene/quality gates observational rather than
geometry-solving. Exact suppression identity, not an origin heuristic, is the
reviewable invariant. The as-of label's normal text paint and source identity
are unchanged. The only expected migration is two HALCYON rendered labels and
their placement warnings. Residual risk: a new non-label suppression family
requires an explicit corresponding gate mapping rather than a guessed ID.
