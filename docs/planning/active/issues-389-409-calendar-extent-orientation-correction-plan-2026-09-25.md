# Design Correction Plan — Calendar-Closed Extent Orientation (#389, #409)

**Trigger:** I3 final evidence review found that the generic extent resolver
replaced a closed-day stripe's date-column width with the whole timeline width.
That contradicts the completed `calendarClosed` placement contract and #409's
one-stripe-per-closed-day outcome.

## Required sequence

1. Publish the semantic-direction correction and its architecture review.
2. Constrain `calendarClosed` to the timeline in the v0.6 profile contract.
3. Make Layout preserve a calendar stripe's inline date interval while using
   the completed timeline block extent; keep row-oriented backgrounds' inline
   extent selection unchanged.
4. Add a distinct-width characterization test, regenerate all public evidence,
   and run the focused, full, coverage and materializer gates.

## Completion gate

Every closed-day placement has its own measured date-column inline bounds, the
timeline's block bounds, and no renderer infers or expands either dimension.
