# Design Correction — Typed Table Allocation Closure (#403, #404)

**Status:** Accepted correction to P1/I2 before measured-column implementation.

## Finding

View v0.16 accepts column alignment, logical width, and `hierarchyColumn`, but
the current View-to-surface adapter reduces every column to `(id, label)`.
Layout therefore cannot distinguish declared allocation intent and still
indents the first source-ordered column. That is a broken ownership boundary.

## Typed presentation ingress

The review adapter creates renderer-neutral `TableColumnContent` values with
stable id, header text, finite alignment, and normalized closed width. Surface
content and the presentation contract carry them unchanged to Layout alongside
the optional named hierarchy column. Scene receives only completed placements.

## Measured allocation

Layout measures each column's preferred width from header and visible cells,
including existing cell inset. `content` and `minmax.min: content` reserve the
preferred width. `fill` and `fr` are flexible; their lower bound is the
measured ellipsis floor, not an unowned numeric constant. Flexible columns
share remaining inline space by their finite declared weights; at most one
`fill` remains a View invariant. A flexible column can shrink only to its
ellipsis floor and only under `ellipsize-with-source`. No legal allocation
raises `E_LAYOUT_TABLE_OVERFLOW`; `diagnose` never silently shrinks text.

## Alignment and hierarchy

Layout ellipsizes against final text allocation, then positions measured text
at `start`, `center`, or `end`. Header and cell use the same column intent.
Only the id named by `hierarchyColumn` receives row indentation. Indentation
consumes the cell allocation before text fitting and alignment. No condition
may inspect column index to select hierarchy geometry.

## Boundaries and non-goals

View owns table intent. Layout owns measurement, allocation, ellipsizing,
alignment, and indentation. Theme supplies typography; Scene and adapters
project completed placements. This adds no spanning header, totals, arbitrary
width syntax, new Theme token, or table paint-role policy (#402).
