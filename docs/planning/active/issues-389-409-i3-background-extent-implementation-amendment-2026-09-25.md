# Implementation Amendment — I3 Background Extent (#389, #409)

**Supersedes for I3:**
`issues-404-403-388-389-409-table-timeline-composition-i3-background-amendment-2026-09-25.md`.

## Atomic implementation slice

1. Add `layout-profile/v0.6` and its typed resolver/model fields for the
   required `reviewSurface.backgroundExtents` mapping.  Remove v0.5 ingress;
   migrate layouts, Context closures, schema/resource inventories and tests in
   the same change.
2. Retain View `rowDecoration` only as selection intent and add the finite
   `rowBand` semantic binding and Theme role migration.
3. Give Layout one extent resolver for `rowBand`, `groupBand`,
   `groupHeaderBand` and `calendarClosed`.  Emit all selected background shapes
   with resolved bounds, truthful slot/container identity, semantic id and
   Theme-supplied paint order.
4. Add Layout validation for intersecting translucent fill backgrounds and
   verify alternation suppresses the competing body fill family.
5. Reduce Scene to direct shape projection.  Add focused schema, extent,
   overlap and projection tests; regenerate materializer evidence; run focused
   tests, full pytest, public materializer checks and SVG diff review.

## Acceptance

- A row band defaults to the table region and never compounds calendar fill in
  the timeline.
- The four background roles declare all physical reaches in a v0.6 Layout
  Profile; no Scene or renderer infers them.
- Every public context remains materializable, no v0.5 reader remains, and
  generated output changes only as intended.
