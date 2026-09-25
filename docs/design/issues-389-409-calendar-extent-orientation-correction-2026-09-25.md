# Design Correction — Calendar-Closed Extent Orientation (#389, #409)

**Status:** Accepted correction to I3 before implementation publication.

## Problem

`backgroundExtents` was correctly introduced to select the horizontal reach of
row-oriented bands.  Applying that same transformation to `calendarClosed`
discarded the semantic's already-measured day-column interval and widened every
closed-day stripe to the full timeline.  The result is neither a calendar
closure nor a completed-placement projection.

## Directional contract

The finite semantic role determines which axis a review-surface extent may
resolve:

| Semantic | Variable axis | Fixed axis |
| --- | --- | --- |
| `rowBand`, `groupBand`, `groupHeaderBand` | inline reach selected by `table`, `timeline`, or `both` | authored row/group block span |
| `calendarClosed` | authored date-column inline interval | completed timeline block span |

`calendarClosed` is therefore fixed to `timeline` in the v0.6 Layout Profile
schema.  It is retained as an explicit required mapping member so the profile
states the calendar's physical domain, but `table` and `both` are invalid for
that role.  Layout uses the authored date interval as the stripe's inline
bounds and the timeline slot as its block bounds.  It does not treat the value
as a generic rectangle-widening instruction.

## Boundaries

View still selects only finite decoration membership.  Layout Profile supplies
the finite review-surface arrangement.  Theme supplies treatment, opacity and
paint order.  Layout alone combines these inputs into a completed rectangle;
Scene and every materializer project it verbatim.  The existing overlap rule
continues to compare completed fill areas, so outline calendar stripes remain
non-area paint and cannot mask an invalid fill overlap.

This correction is a v0.6 clarification, not a compatibility path: no v0.5
runtime ingress, coordinate-bearing View field, Theme extent key, or renderer
geometry recovery is introduced.
