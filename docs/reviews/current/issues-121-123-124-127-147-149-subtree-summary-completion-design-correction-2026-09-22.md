# Subtree Summary Completion Semantics — Design Correction

**Amends:**
`issues-121-123-124-127-147-149-wbs-view-selection-design-correction-2026-09-22.md`

## Trigger

P4 implementation reached the summary-normalization boundary and found that the
published correction defines the `scope: subtree` member set but not the value
of a typed `source: {object, facet: planned}` metric over that set.  Choosing an
ad hoc minimum, maximum, or renderer-local envelope would make the summary
meaning depend on implementation detail.

## Completed metric meaning

`scope: subtree` is legal only on a typed metric whose source is
`{object: <selected-primary-id>, facet: planned}` in a `grouping.by: hierarchy`
View.  It retains the existing scalar planned-source meaning for each member:

* a span contributes its planned `end`;
* a point contributes its planned `at`.

The normalized metric value is the latest contributing date in the selected
subtree.  It is therefore the **planned completion** of that View-selected
subtree, not a schedule mutation, a parent rollup recalculation, or a visual
envelope.  The root itself and its selected descendants contribute in View
projection order; primary membership is de-duplicated before values are read.
Snapshot and Actual comparison tracks never contribute a second member or a
second value.

The selected root must be a primary Project member in the View projection.  A
missing root, a non-primary source, a non-hierarchy View, or a metric with no
known planned contribution is rejected with the summary normalization
diagnostic rather than silently falling back to an object-level value.  The
closed summary schema admits `scope: subtree` only for this typed object source;
the existing catalog string sources and an unscoped object source remain
unchanged.

## Responsibility and architecture review

Project Core remains the authority for normalized parentage, planned facts, and
rollup schedules.  View projection determines selected roots, descendant
membership, order, and primary-track de-duplication.  Summary normalization
turns those immutable View facts into one scalar completion date.  Layout only
measures and positions the resulting text or the separately completed
`summaryBar` placement; Scene only projects placements; renderers serialize
Scene primitives.  No presentation layer traverses raw Project mappings,
recomputes a schedule, or derives an aggregation from table text or Scene
geometry.

This correction introduces neither compatibility parsing nor a general
aggregation language.  A future metric operation requires a separately typed
summary contract and design review.
