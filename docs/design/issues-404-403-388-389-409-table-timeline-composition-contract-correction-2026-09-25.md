# Design Correction — P1-I1 Table Intent Closure (#404, #403, #388, #389, #409)

**Status:** Accepted correction to the P1 design and its existing table-declaration correction.

## Finding

The initial v0.16 implementation draft introduced a separate object spelling
for column widths (`{content: true}` and `{fill: true}`), while the approved
design says that View column intent uses the existing logical size vocabulary.
It also omitted the approved `rowDecoration` View declaration.  Both are
contract incompleteness, not implementation details: accepting either would
make Layout infer author intent that the View did not declare.

## Corrected v0.16 contract

`tableColumns` remains the ordered top-level View declaration and
`hierarchyColumn` remains its optional sibling.  Column `width` has exactly
the table subset of the established Layout logical size grammar:

```yaml
tableColumns:
  - id: title
    source: title
    missing: em-dash
    align: start
    width: {minmax: {min: content, max: {fr: 1}}}
  - id: delta
    source: {facet: finishDelta}
    format: signedDays
    missing: em-dash
    align: end
    width: content
```

The permitted forms are `content`, `fill`, `{fr: positive-number}`, and
`{minmax: {min: content, max: content | fill | {fr: positive-number}}}`.
`fixed`, `fitContent`, and `aspectRatio` remain intentionally unavailable to
table columns: a View selects semantic presentation intent, while fixed
physical geometry belongs to Layout Profile metrics.  At most one `fill`
allocation is accepted; Layout will enforce this allocation invariant in I2.

View also carries the finite, coordinate-free declaration:

```yaml
rowDecoration: {mode: none | alternate-rows | alternate-groups}
```

Its absence means `none`.  It is table--timeline-only, as are
`tableColumns` and `hierarchyColumn`.

## Binding typed-contract invariants

The parser rejects duplicate table column IDs, an unknown hierarchy column,
`hierarchyColumn` without visible nesting, and visible nesting without one.
Visible nesting means automatic `grouping.by: hierarchy`, or an explicit row
with a nonzero depth or `parentRow`.  This validates only View composition;
it neither parses WBS codes nor asserts that an explicit row tree is Project
hierarchy.

## Migration impact

All v0.16 corpus Views use the corrected scalar/object grammar and declare
`rowDecoration` explicitly.  There is still no v0.15 reader.  The correction
does not add allocation behavior: I2 remains the owner of measured width and
row allocation, and I3 remains the owner of completed decoration placements.
