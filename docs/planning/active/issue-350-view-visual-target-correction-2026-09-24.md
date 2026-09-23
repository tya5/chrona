# Design Correction: View Visual Target Closure (#350)

**Status:** Complete — blocks I350R-4 implementation until its schema and
Layout projection ship atomically.

## Observed discrepancy

Specification 64 describes closed `view/v0.12` `visuals`, but the published
v0.12 schema and `ViewInput` have no such field.  The only implementation is
the obsolete internal `icon_bindings` seam, which supports one object leading
label or mark and is deliberately not authorable.  Adding a broad `visuals`
schema before a resolver would recreate the forbidden valid-but-unprojected
door.

## Closed target model

One View `visuals` entry has a typed `target`, direct `ref` or field
`encoding`, `side` (leading or trailing, default leading), and `decorative`.
Exactly one entry per resolved target/side is admissible.  The v0.12 schema is
introduced only with all of these Layout mappings:

| Target kind | Selector | Layout placement identity family |
| --- | --- | --- |
| `title` | none | `title` |
| `column` | column id | `column:{id}` |
| `cell` | object id and column id | `cell:{object}:{column}` |
| `group-header` | group id | `group-header:{id}` |
| `plot-label` | object id | `member-label:{id}` |
| `annotation` | annotation id | `annotation-text:{id}` |
| `note-index` | annotation id | `note-index:{id}` |
| `legend` | semantic role | `legend:{role}` |
| `summary` | panel/metric identity | `summary:{id}` |
| `milestone` | milestone identity | `milestone:{id}` |
| `axis-label` | axis level/index or all | `axis-label:{level}:{index}` |
| `as-of-label` | none | `as-of:*` |
| `mark` | object id and facet | `planned:{id}` or `actual:{id}` |

The schema must omit a target family when that family is absent from the
current surface; a selector resolving to zero or multiple placements rejects.
Encoding is admitted only for `plot-label`, `cell`, and `mark`, where the
selected object field is already exposed by the projection.  It maps exact
field values to `set:name`; an unknown, absent value, missing catalog, or
unknown icon rejects before text placement.

## Ownership and composition

`ViewInput` transports immutable requests only.  Layout resolves them against
closed `IconAsset`s, reserves both advances before measuring/wrapping text,
uses typography/cap height and Theme ratios, and emits completed `IconPlacement`
with label-vs-mark paint role and logical reading order.  Scene consumes only
that completed placement.  The internal `icon_bindings` field is removed in the
same slice; it cannot coexist as a second occurrence-selection path.

This preserves Project/Actual fact authority, Context catalog closure, Theme
paint authority, Layout geometry ownership, and adapter projection boundaries.
