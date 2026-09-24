# Design Correction Plan: Overlay review-height token (#382)

**Status:** Accepted.

## Trigger

The initial current-Context materialization found that the 26-row programme
board requires a 900px timeline allocation.  An overlay child sized as
`content` receives only its measured preferred 780px; a guide below the title
then cannot make the required review region materializable.  Existing wallboard
Theme tokens name sidebar width but no reusable review-region block extent.

## Decision to establish

Determine whether the clean bounded expression is a Theme number token used by
the new Layout Profile, rather than a raw Layout number, a `safe` overflow
escape, or a misleading corpus selection reduction.

## Required outputs

* An English correction design and architecture review.
* An implementation amendment that adds a scoped wallboard Theme token and
  includes it exactly in Layout's `requiredThemeTokens`.
* Materializer evidence that the guide-offset fixed review region is feasible
  at its declared viewport.

## Guardrails

* Do not reduce the programme selection merely to hide layout infeasibility.
* Do not use `safe` clipping for required table/timeline content.
* Do not place a raw numeric height in Layout; Theme remains the reusable owner
  of concrete distances.
