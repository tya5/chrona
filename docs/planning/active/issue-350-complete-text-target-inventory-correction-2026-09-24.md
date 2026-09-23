# Design Correction: Complete Text Target Inventory (#350)

**Status:** Complete — extends I350R-4 before its target inventory is accepted.

## Finding

The original View target table omitted three existing completed text placement
families: project notes (`note:{id}`), group details
(`group-detail:{id}`), and coarse axis bands (`axis-band:{level}:{index}`).
It also left finish-variance labels (`variance:{instance}`) without a stable
View occurrence selector. Omitting them silently would contradict R350-06's
all-label goal.

## Closed successor inventory

The following forms are added to the View discriminated union and map exactly
to the named Layout placements:

| Kind | Selector | Placement |
| --- | --- | --- |
| `note` | `id` | `note:{id}` |
| `group-detail` | `id` | `group-detail:{id}` |
| `axis-band` | `level`, `index` | `axis-band:{level}:{index}` |
| `variance-label` | `object` | `variance:{object}` |

`variance-label` is admitted only when automatic projection produces one
object-owned variance label. Repeated explicit-row instances are deliberately
rejected rather than selecting an arbitrary row; a future row-instance target
would require a separate source-contract design. The existing `plot-label`
target likewise maps only the object-owned member-label family and rejects
ambiguous repeated rows.

Every other current text placement is now covered by one target kind:
title, column, cell, group header/detail, plot/variance label, annotation,
project note/note index, legend, summary, milestone, axis band/label, and
as-of label. Direct references are valid for all forms. Field encoding remains
limited to object-owned `cell`, `plot-label`, and `mark`; the new forms have no
projection-exposed field source and reject encoding in schema.

## Architecture consistency review

The correction adds no generic matching or presentation-side fact lookup.
View names a stable source-owned occurrence, Layout resolves the completed
placement and computes geometry, and Scene still projects only the result.
The explicit ambiguity rejection preserves the same fact and row authority as
the existing annotations and marks design.

## Acceptance

The I350R-4 target-inventory fixture must exercise every listed form under a
surface that produces it, including the four additions above, and must prove
that repeated-row `plot-label`/`variance-label` selection rejects rather than
choosing by order.
