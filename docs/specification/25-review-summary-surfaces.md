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

**Panel arrangement (#1190).** A Summary Profile panel may declare
`arrangement: stack | inline`; omission means `stack`. Stack retains the existing
run order, placement identities, content and typography. Inline arranges that
panel's ordered runs on one common baseline; panels themselves remain vertically
ordered. For `figures`, the panel title is a `summary-caption`, each formatted
metric value is `metric`, and its declared label is `summary-unit`. Multiple
metrics keep their declared order. For `lines` and shorthand metrics, the title
and each already-composed metric string use `summary-caption`; their content is
not parsed to infer a separate unit. Theme declares the inline gap after a run,
with zero when absent and no gap after the final run. Layout measures each run
with its selected Theme treatment and completes the run origins, shared baseline
and panel extent before Scene construction.

When any panel uses `inline`, run identities are structural addresses:
`summary:/panels/<index>/title` and
`summary:/panels/<index>/metrics/<index>/(value|label|text)`.
Authored IDs and source provenance remain unchanged; punctuation or repeated
IDs cannot alias measured runs. Addresses follow the ordered profile, without
a cross-reordering identity promise. Every run, including mixed stack panels,
carries explicit semantics. All-stack profiles keep their legacy identities.

A dark delivery-control composition is also a user-editable resource set. The adapter
MUST interpret only declared metrics and panels; it MUST NOT contain a dashboard-specific
score, panel list, or title-based branch.

`missingActualCount` (and its typed `count.missingActual` source) counts only
selected Primary items whose View-projected observation state is
`due-unobserved` at the explicit Actual `asOf`. Without an Actual as-of the
metric is unavailable, not zero. An incomplete but selected observation and
future work are not counted. Summary formatting does not independently
interpret planned or Actual dates.

View count figures (Spec 06 §7.2) use this same projection-owned count producer.
Their neutral integer bundle is passed to Core's closed selector; no consumer re-derives
observation state or counts lane/comparison occurrences. Behind/ahead remain counts of
known positive/negative observed finish deltas, not a critical-path forecast.
