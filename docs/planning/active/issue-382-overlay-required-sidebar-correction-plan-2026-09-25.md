# Design Correction Plan: Overlay required-sidebar scope (#382)

**Status:** Accepted.

## Trigger

The first overlay composition placed the programme-board's optional legend in
the new sidebar and exposed an unrelated multi-line detail-rail overlap.  That
policy is not part of #382's overlay grammar evidence and is already covered
by existing wallboard composition work.

## Decision to establish

Retain only the required title in the overlay sidebar.  Its bounded end forms
the barrier used by the required table/timeline region.  Summary, notes, and
legend remain absent from this narrowly-scoped Context rather than becoming an
unreviewed detail-rail redesign.

## Required outputs

* An English correction design and architecture review.
* An implementation amendment that removes optional detail slots from the new
  Layout only, while retaining guide, barrier, and anchored required slots.
* Regression evidence that no existing wallboard artifact changes.
