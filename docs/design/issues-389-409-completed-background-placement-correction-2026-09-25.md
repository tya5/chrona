# Design Correction — Completed Background Placements (#389, #409)

**Status:** Accepted correction to P1/I3 before decoration implementation.

## Finding

Theme v0.10 already admits `backgroundTreatment` and
`backgroundPaintOrder`, but no runtime reads them. More importantly, Layout
currently completes only calendar geometry while Scene reconstructs group and
header bands from group bounds. That lets Scene decide background geometry and
emission order, contrary to the placement architecture.

## Completed decoration closure

Layout will emit every review-surface background as a `ShapePlacement` with a
semantic id, resolved cross-slot bounds, slot identity, and supplied paint
order. It emits `row-band:<row>` or `group-band:<group>` only when the View's
finite `rowDecoration` selects that member. Their inline bounds start at the
table slot and end at the timeline slot; their block bounds are exactly the
resolved row or group content bounds. Header bands and calendar closures use
the same completed shape path.

Scene maps each shape's semantic id to the registry binding and projects its
given bounds and paint order verbatim. It neither derives a group rectangle
nor chooses an ordering. SVG/PNG consume stable Scene primitive order.

## Background conflict rule

Theme exposes a typed background treatment and paint order only for the finite
background roles. Layout resolves paint before validating completed shapes.
Two shapes with translucent `fill` treatment may not intersect. An `outline`
calendar closure may intersect a fill because it has no area paint. This is a
geometric invariant over completed bounds and resolved opacity, not a role-name
or adapter-order convention. It removes alpha compounding instead of choosing
which translucent background wins.

## Scope

The correction keeps View coordinate-free and Theme appearance-owned. It does
not introduce generic z-index, blending, arbitrary row selectors, or #402
table cell role selection. Required shipped-theme migration chooses one
background family to remain a fill where needed and uses outline treatment for
overlapping calendar closures.
