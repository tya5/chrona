# Implementation Review — I3 Completed Background Placements (#389, #409)

**Result:** Accepted for publication.

## Delivered contract

`layout-profile/v0.6` atomically replaces v0.5 runtime ingress and requires a
closed `reviewSurface.backgroundExtents` mapping.  The three row-oriented
semantics select their finite inline reach through `table`, `timeline`, or
`both`; `calendarClosed` is schema-constrained to `timeline` and retains its
measured day-column inline interval.  Layout records this in its typed manifest
and composes the final primitive geometry, including the synthetic
`review-surface` identity for `both` bounds.

The View's finite `rowDecoration` selects membership only.  Theme owns the
finite role's treatment, opacity and paint order.  Scene no longer overrides
completed background slot ownership and does not measure, route or widen a
background.  Outline treatment now removes area fill across SVG, Typst and
TikZ projection, preventing a nominally outline calendar stripe from silently
becoming a translucent fill in a non-SVG target.

## Structural checks

- Schema fixtures reject an omitted required extent mapping; the calendar role
  cannot be assigned `table` or `both`.
- Characterization covers table-only alternate row bands, calendar day width
  smaller than the timeline width, projected outline paint, and invalid
  intersecting translucent fills.
- Layout validates completed background fill intersections rather than relying
  on role names or construction order.
- The shipped Aster overview contains table-only row-band rectangles.  The
  Controller-Z elevated SVG contains each calendar closure as an unfilled,
  stroked date-width stripe.

## Verification

Executed after regeneration on 2026-09-25:

```text
pytest -q                                      806 passed, 19 skipped
tools/presentation_coverage.py --check          passed
tools/corpus_coverage.py --check                passed
tools/validate_schema_references.py             passed
git diff --check                                passed
```

All 21 public manifest slide targets were materialized through the public
materializer with `--write`; the resulting scene and SVG artifacts are included
in this publication.  The retained v0.5 schema is inventory-only/package
evidence; no v0.5 Layout Profile remains a runtime ingress.
