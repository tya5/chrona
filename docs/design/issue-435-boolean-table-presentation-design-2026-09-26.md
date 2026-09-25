# Issue #435 Boolean table presentation design

## Decision

`view-v0.20` replaces the live `view-v0.19` contract.  Table `format` becomes
a closed tagged presentation value:

```yaml
format:
  kind: presence
  whenTrue: Missing
  whenFalse: Recorded
```

`whenTrue` and `whenFalse` are required strings and may intentionally be
empty.  They are named after the boolean value, rather than after a particular
domain concept, so the contract remains truthful for a boolean custom field as
well as `comparisonFacet: missingActual`.  Existing non-boolean format kinds
remain finite strings (`text`, `dateRange`, `date`, and `signedDays`).

The schema migration is replacement, not a compatibility reader: all live
Views move to v0.20 and v0.19 becomes an inventory-only transitioning schema.

## Boundary and data model

`TableColumn.format` is a typed closed union.  Its presence variant is
`BooleanPresencePresentation(when_true, when_false)`; its other variants are
the existing named formatter values.  Raw View maps stop at resource parsing.

At resource ingress, a `missingActual` column must use the presence variant.
During review-content normalization, a resolved boolean from any other source
must also use it.  The latter check handles author-defined fields whose value
type cannot be known from View syntax alone.  Both failures use the stable,
actionable `E_VIEW_BOOLEAN_PRESENTATION` diagnostic before any Layout
measurement.

`display_value` accepts the typed format union.  For a boolean, it returns the
selected declared string.  It rejects a boolean in every other format branch;
there is no `str(bool)` fallback.  `TableCellContent` remains `str`, so Layout,
Scene serialization, and adapters retain no boolean-specific decision or
branch.

## Corpus disposition

The single shared HALCYON View changes the `Obs` column to the presence variant
shown above.  Thus `missingActual: true` renders `Missing` and `false` renders
`Recorded`; both remain legible without relying on the low-contrast
`missingActualCell` paint.  #431 separately owns contrast policy and may
improve that paint without changing this authoring meaning.

## Architecture review

| Boundary | Responsibility | Explicitly excluded |
| --- | --- | --- |
| View schema/parser | Require and normalize author intent | Fact lookup, text measurement |
| Review content | Resolve boolean fact and choose declared string | Scene geometry or rendering |
| Layout | Measure and allocate the resulting string | Boolean interpretation |
| Scene/adapters | Transport/project completed text | Formatter defaults or `str()` |

The design reuses the existing typed presentation flow and does not introduce
a renderer-only exception, an untyped formatter map, or an icon sub-language.
It is therefore consistent with the completed Layout → Scene projection
architecture and with #446's future Scene-only evaluation boundary.

## Acceptance invariants

1. A boolean cannot reach generic text conversion.
2. Both boolean values yield deterministic declared text.
3. A `missingActual` View without `presence` is rejected before materialization.
4. The three HALCYON artifacts have no `True` or `False` table text and retain
   reachable `table-missing-observation` realization evidence.
