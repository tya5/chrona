# Review Summary Surfaces Design

**Status:** Design complete  
**Owns:** M16 read-only summary metrics and panel composition.

Summary panels are a separate projection over the selected M15 rows. The closed metric
catalog is: `selectedCount`, `actualCoverage`, `knownFinishVarianceCount`,
`nextPlannedPoint`, and `missingActualCount`. `actualCoverage` is a pair of known
Actual-bearing selected objects and eligible selected objects; a zero denominator is
`unknown`, never 0% or 100%. `nextPlannedPoint` is the earliest selected planned point
after the explicit Render Context as-of date, or unavailable. A finish variance is
counted only when its aligned endpoints are known.

Every panel is profile-selected, has a stable ID, and references its metrics by name.
It carries metric provenance, denominator/availability state, and text alternative into
Scene/Output. A panel is not a Project field, does not create risk workflow, and does
not infer progress, health, probability, or forecast. Layout is profile geometry;
Theme supplies only declared panel roles and tokens.

A dark delivery-control composition is also a user-editable resource set. The adapter
MUST interpret only declared metrics and panels; it MUST NOT contain a dashboard-specific
score, panel list, or title-based branch.
