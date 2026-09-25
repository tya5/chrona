# Design Correction — Review-Surface Background Extent (#389, #409)

**Status:** Accepted correction to I3 before implementation.

## Problem

The original completed-background design assigned every selected row and group
band a rectangle from the table's left edge through the timeline's right edge.
That makes a translucent row band and a calendar closure occupy the same
timeline region.  Reordering those primitives cannot make two translucent
fills legible; it only selects a different compounded colour.

The error is one of ownership.  `rowDecoration` answers *which semantic
members exist*, while a rectangle's horizontal reach answers *how the
review-surface slots are arranged*.  Neither is a Theme paint value and neither
may be inferred by Scene.

## Contract

`layout-profile/v0.6` replaces v0.5 and adds a required finite
review-surface declaration:

```yaml
reviewSurface:
  rowDistribution: pack
  backgroundExtents:
    rowBand: table
    groupBand: timeline
    groupHeaderBand: both
    calendarClosed: timeline
```

Each value is one of `table`, `timeline`, or `both`.  The mapping has exactly
the four completed background semantic ids above; it is not an arbitrary
primitive selector, a CSS-like layer, or a generic container option.  A v0.6
profile must name every member so the chosen physical arrangement is visible in
the resource and reviewable with the rest of the profile.

Layout resolves `table` and `timeline` to their corresponding completed slot
bounds.  `both` is their union from the table inline start to the timeline
inline end.  A single-slot ShapePlacement carries that slot id.  A `both`
placement carries the existing review-surface container identity rather than
falsely claiming either child slot.  This makes a primitive's identity agree
with its extent.

## Composition

The View remains exactly coordinate-free:

```yaml
rowDecoration: {mode: none | alternate-rows | alternate-groups}
```

`none` preserves each group body band; `alternate-groups` emits every second
group body band; `alternate-rows` emits every second row band and suppresses
group body bands.  Group header bands remain independent because their block
bounds do not overlap group content bounds.  This gives one row-oriented fill
family at a time.

Theme continues to own the finite roles' `backgroundTreatment`, resolved
opacity, and `backgroundPaintOrder`.  Layout validates the completed shapes:
two intersecting translucent `fill` shapes are invalid.  An `outline` may
intersect a fill because it has no area paint.  The rule compares resolved
bounds and resolved alpha; it does not rely on construction order or role
names.  The shipped profile mapping above puts the selected row band in the
table and the calendar closure in the timeline, while the existing calendar
outline remains valid where a group band occupies the timeline.

## Boundaries and migration

This is a structural Layout Profile contract change, so v0.5 is not retained
as a runtime ingress.  All layouts, Context closure fixtures, package resource
inventory and generated public evidence migrate atomically to v0.6.  The
change does not add coordinates to Views, extent keys to Themes, generic
z-index, blending, arbitrary selectors, or renderer layout inference.

Scene projects each Layout ShapePlacement's semantic binding, bounds, slot
identity and paint order verbatim.  SVG and PNG consume Scene order only.
