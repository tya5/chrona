# Review Detail Profile v0.1

**Status:** Design complete — M23 input contract

## Ownership and boundary

A Review Detail Profile is a presentation resource (`kind: review-detail-profile`)
consumed only after View selection and Layout solving.  It composes existing facts; it
does not change Project, schedule, Actual alignment, or summary metric semantics.

It may declare four optional surfaces:

- `legend`: ordered semantic roles (`planned`, `actual`, `variance`, `milestone`,
  `dependency`) with user-facing labels;
- `groupDetails`: presentation-only label and bounded description keyed by the
  View-selected group ID;
- `milestones`: a View-selected ordered list of point object IDs; their title and
  scheduled date are derived from the existing projection;
- `observations`: a read-only, source-labelled table. Rows are literal presentation
  observations with stable IDs, cells, and an optional emphasis role. They must carry a
  `source` string and cannot be used by scheduler, Actual reconciliation, or summary
  metrics.

This keeps external supplier notes visibly attributable without fabricating Actual or
turning slide content into scheduling input.

## Layout integration

For the v0.2 design successor, `29-schema-owned-presentation-settings.md` and the
`detail` definition in `presentation-settings-v0.2.schema.json` are the single
contract for legend labels, templates and formatters. Do not add a parallel legend
configuration in Layout or Theme. Other M23 panels remain deferred.

The Layout Profile may allocate `legend`, `observations`, and `milestones` slots.  The
solver allocates them from declared regions and emits their rectangles; no coordinates
are stored in a resource. Required unavailable sources diagnose.  The SVG adapter draws
in logical slot order and retains source metadata for every derived item.

## M23 acceptance rules

1. A preset changes all labels, descriptions, legend order, milestones, and observation
   rows through resources, never preset/title/sample branches.
2. Unknown milestone IDs, unsupported legend roles, duplicate row IDs, overfull required
   slots, and missing observation provenance diagnose deterministically.
3. Plan/Actual bars, dates, and variance continue to originate only in the existing
   Review Projection.
4. The same Project/View/Style/Theme/Layout/Detail closure produces identical SVG.
