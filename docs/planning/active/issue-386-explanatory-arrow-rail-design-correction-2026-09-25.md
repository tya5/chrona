# Design Correction: Explanatory-Arrow Rail Placement (#386)

**Status:** Accepted correction to #386 annotation placement.

## Trigger

The declared full-width rail materialized far from the timeline endpoints, but
the current composer uses its rail/fallback algorithm only when
`purpose == callout`.  An `explanatory-arrow` always attempts direct
anchor-adjacent placement, so it cannot use the declared rail and fails with
`E_PRESENTATION_LABEL_UNPLACEABLE`.

## Corrected decision

`callout` and `explanatory-arrow` share the Layout-owned candidate placement
algorithm.  Both may use the View's `visibility.fallback.annotations` ladder,
including `rail` and `suppress`; both retain their distinct semantic purpose in
completed Scene primitives.  `note` and `highlight` retain direct placement
because they do not claim the same explanatory leader treatment.

The evidence View declares `[rail, suppress]`; its two explanatory arrows use
the full-width rail and still receive endpoint-to-box leaders.  The selected
rung is a completed Layout decision, not a renderer interpretation.

## Required verification

- An explanatory arrow reaches a declared rail through the same finite
  candidate policy as a callout.
- A missing rail candidate fails/suppresses according to the declared View
  ladder, not an implicit purpose-specific fallback.
- Scene preserves `explanatory-arrow` for box, text, and leader provenance
  while adapters remain unaware of candidate selection.
