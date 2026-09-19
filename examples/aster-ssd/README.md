# ASTER Enterprise SSD sample

This is a fictional development program. Dates, observations, holidays and risks
are demonstration data, not a real product commitment or a national calendar.

## Design contract

One authoritative Project contains 24 objects across six teams and 28 dependency
edges. It combines fixed tasks, fixed gates, scheduled work, start-to-start
overlap, finish-to-start sequencing, multi-predecessor convergence, calendar-day
stress duration, two work calendars, calendar exceptions, calendar-qualified lag,
anchors and an upper-bound constraint.

Actual observations remain separate from the plan. Revised observations exercise
latest-sequence selection. Missing and unmatched observations remain explicit.
Actual dates do not reschedule the baseline or imply a forecast.

## Visual direction

Use an ink/navy background, amber plan bars and cyan observed bars. Team section
headings replace Controller Z's merged owner column. The wider work-item column
and sectional whitespace provide a distinct layout without a custom renderer.

Four 1600 × 900 slides share one design: an eight-item executive selection,
platform/firmware, performance/security, and qualification/production. Three
detail slides cover every object once. A tall master view shows all objects and
all dependencies, including edges across slide boundaries. Per-slide edges only
connect selected endpoints; no invented transitive edges are drawn.

All resources use existing schemas. No new engine feature, hardcoded ASTER
renderer branch, or preset inheritance is needed. Complete settings avoid the
known unresolved preset-reference contract. This sample does not claim to close
the prior P1–P5 review findings. Partial-progress bars, actual milestone markers,
federation and interactive editing are outside this rendered sample's scope.
