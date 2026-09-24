# Design Correction: Annotation Rail Feasibility (#386)

**Status:** Accepted correction to the previous #386 allocation correction.

## Trigger

The first correction placed a required annotation rail beside the existing
table/timeline review row.  Public materialization then failed with
`E_LAYOUT_REQUIRED_OVERFLOW`: that third required column competes with the
already-required table and timeline minima at the declared 1600px viewport.

## Corrected decision

The dedicated Layout reserves annotations as a **full-width fixed-height rail
below the review row**, rather than a third review column:

```text
title
table | timeline
footer
annotations rail (full inline width, fixed panel.minimum block extent)
```

The review row keeps its established feasible allocation.  The rail receives a
declared `panel.minimum` height and full available inline width, so two
measured boxes can be placed and their leaders can cross from timeline
endpoints without asking the renderer to resolve capacity.

## Required verification

- The dedicated Layout solves at the declared 1600×900 viewport without
  `E_LAYOUT_REQUIRED_OVERFLOW`.
- Both required boxes fit in the reserved rail without suppression.
- The original executive Context remains byte-identical, proving no control
  layout was altered.
- The final public SVG proves route avoidance using completed Layout geometry.
