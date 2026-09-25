# Table--Timeline Composition Design (#404, #403, #388, #389, #409)

**Status:** Proposed design; implementation is not authorized until architecture review and implementation plan are published.

## Decision

Replace positional table/row assumptions with one View-to-Layout composition
contract. The contract has three independent inputs:

```text
Project hierarchy       -> semantic parent/child and optional WBS code
View table/hierarchy    -> selected content and finite presentation intent
Layout Profile/Theme    -> available surface, spacing, row surplus and paint
                              ↓
                    Layout placements (including cross-slot decorations)
                              ↓
                    completed Scene primitives and paint order
```

Neither a Scene builder nor an output adapter decides hierarchy, a table column,
row allocation, decoration extent, or paint precedence.

## 1. Hierarchy has one semantic source

Project parent/child relations are the authoritative hierarchy. `wbsCode` is an
optional, unique Project display value; it is not parsed to infer a parent.
`path` is derived from the same resolved Project hierarchy. A View has two
different, explicit uses of hierarchy:

* automatic rows with `grouping.by: hierarchy` select a bounded projection of
  Project hierarchy. Their row depth and rollup are derived from that
  projection, never separately supplied;
* explicit rows are a presentation composition. Their `parentRow`/`depth`
  describe row nesting only, are validated as one acyclic row tree, and do not
  claim or modify Project hierarchy.

An automatic View cannot carry explicit rows, so the two forms cannot be mixed.
An explicit row's table subject may display `wbsCode` or `path`, but no equality
between a user-authored WBS string and display depth is inferred or required.
This preserves the existing domain distinction rather than inventing a false
validation rule.

`hierarchyColumn` is required when a table-timeline View declares any visible
row nesting. It names exactly one declared column. The named column receives
the completed indent; source order has no effect. A View with no nesting omits
it. An unknown column, a hierarchy column without nesting, or nesting without
a hierarchy column is a View diagnostic.

## 2. Table column intent is finite and measured

View v0.16 replaces the v0.15 table-column object atomically; v0.15 is not
retained as a compatibility reader. Each column declares:

```yaml
table:
  hierarchyColumn: title
  columns:
    - id: index
      source: rowIndex
      format: text
      missing: em-dash
      align: end
      width: {content: true}
    - id: title
      source: title
      format: text
      missing: em-dash
      align: start
      width: {minmax: {min: content, max: {fr: 1}}}
    - id: finish-delta
      source: {facet: finishDelta}
      format: signedDays
      missing: em-dash
      align: end
      width: {content: true}
```

`align` is `start`, `center`, or `end`. `width` reuses the Layout Profile's
closed `content | fill | {fr} | {minmax}` size grammar rather than adding a
second sizing language. `content` is the measured header/cell minimum plus
declared cell padding. Fractional columns share only the remaining width after
all minima and gutters. `fill` is valid only once. Layout applies ellipsizing
only under the table slot's declared overflow policy and retains source text in
the existing text placement provenance.

Column header spanning and table totals are deliberately absent from v0.16;
they require a table header-row model and must not be smuggled into width or
alignment fields.

## 3. Rows are content-sized, then distributed

For each completed review row, Layout invokes the existing track feasibility
calculation for that row and combines its result with `timeline.row.minBlockSize`
and a new profile-owned `timeline.row.paddingBlock`. It produces a required
row extent. Group-header extent is added only at a group start.

The profile declares:

```yaml
metrics:
  timeline.row.distribution: pack | fill
```

`pack` is the default: rows retain their required extent and remaining block
space follows the last row. `fill` distributes surplus deterministically among
rows after their required extents; it never changes completed mark geometry.
The total required timeline block is the sum of row extents and headers.

If the total is larger than the slot, Layout delegates to the slot/path overflow
policy defined by the visible-failure design (#400). This design does not add a
second row-specific exception. The current unconditional uniform-row raise is
removed in the same atomic migration.

## 4. Cross-slot decorations are Layout placements

`table-timeline` gains a completed review-surface rectangle: from the table's
inline start through the timeline's inline end, and across each row's completed
block bounds. It is not a Layout Profile overlay node and does not make the
generic layout engine understand table rows.

View has one optional decoration declaration:

```yaml
rowDecoration: {mode: none | alternate-rows | alternate-groups}
```

It selects facts, not coordinates. Layout emits `row-band:<row-id>` or
`group-band:<group-id>` placements only for the selected alternating members.
Theme resolves the corresponding semantic role. Scene receives final bounds,
purpose, role, and `paintOrder`; adapters serialize the supplied order.

The role registry separates `row-band`, `group-band`, and `calendar-closed`.
Theme v0.10 adds finite background-channel treatment `fill | outline` and a
finite integer `paintOrder` for those roles. Shipped themes must satisfy this
invariant: two translucent fill treatments may not overlap in the review
surface. The validation is evaluated from completed placements and paints, not
from role names or SVG order. An `outline` calendar closure is a stroke-only
rectangle/path and remains a calendar fact.

## 5. Completed placement and Scene invariants

The P1 placement closure adds table cell text alignment/available bounds,
per-row required extent, and decoration rectangles. Before Scene construction,
Layout verifies:

1. each hierarchy indentation lies only in the named column and within its
   text allocation;
2. required table text and gutters do not intersect, and allocated widths obey
   their declared size grammar;
3. each row contains its tracks and meets its own minimum;
4. every row/group decoration spans exactly the resolved review surface and
   selected row/group bounds; and
5. overlapping translucent background fills are rejected before Scene.

Scene performs a direct placement projection. The SVG adapter sorts all
primitives by supplied `(paintOrder, stable scene order)`; it has no special
case for row, group, or calendar backgrounds.

## Migration and evidence

This is a clean v0.16/View v0.10/possibly Layout Profile v0.5 migration.
All corpus Views, Themes, layouts, Contexts, schema inventory entries, guides,
and public materializer evidence move in the same release. There is no v0.15
ingress normalizer.

The corpus adds one hierarchy/table fixture with a row index before an indented
title, one signed-days column, heterogeneous stacked row requirements, both
`pack` and `fill` evidence, row alternation across table and timeline, and a
calendar/group combination proving the no-stacked-translucent-fill rule.

## Non-goals

This design does not add table totals, spanning headers, arbitrary cell
formatters, a generic Scene z-index language, project-WBS reconstruction,
adapter-specific blend modes, or vertical text. P2 owns axis behavior; P3
owns semantic role realization; P4 owns typography and orientation.
