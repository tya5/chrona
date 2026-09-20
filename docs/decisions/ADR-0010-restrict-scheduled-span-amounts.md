# ADR-0010: Restrict Scheduled Span Amounts

**Status:** Accepted for Core v0.1

## Context

Calendar-month and calendar-year arithmetic requires a policy for invalid dates.
With clamp semantics, `Jan 31 + 1mo` becomes the final day of February, but reversing
the operation does not generally recover Jan 31. That makes a nominal `1mo` task
duration depend on whether scheduling propagates from start or from end.

Established date libraries expose this same non-invertibility for month arithmetic,
while traditional project-management tools often treat duration units as configurable
working-time quantities rather than calendar-month field arithmetic.

## Decision

Core v0.1 permits calendar months and years as temporal offsets but not as
`schedule.amount` for a scheduled span.

Scheduled span amounts are limited to scheduling-safe amount forms defined by the
Temporal Model.

## Consequences

- task duration remains easier to reason about in forward and backward propagation;
- roadmap annotations and relative dates can still use month/year offsets;
- a future calendar-month duration policy can be added explicitly if demanded by
  real use cases rather than being implied by generic date arithmetic.
