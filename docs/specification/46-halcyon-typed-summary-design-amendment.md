# Issue #46 design amendment: typed v0.5 summary figures

## Trigger

Implementation inspection found that the current v0.5 summary-profile is admitted through the general presentation-resource envelope and its panel metrics are copied as display strings. That does not provide the typed authoring contract approved for HALCYON.

## Decision

A v0.5 panel metric is either a legacy string value or a typed object:

```yaml
metrics:
  actual_as_of:
    label: As of
    source: actual.asOf
    format: date
```

Typed `source` values are `actual.asOf`, `planned.nextPoint`, `count.selected`, `count.missingActual`, and `count.knownFinishVariance`. Typed `format` values are `text`, `date`, `count`, and `signedDays`.
`count.missingActual` follows Specification 25's due-unobserved definition;
it is unavailable without an Actual as-of rather than counting every absent
observation.

## Derived figure source (#586)

A typed metric `source` may also be `{figure: <id>}`, naming a global figure the View declares (Specification 06 section 7.2; Specification 05 section 12.2). Day figures accept `count` (`63`), `signedDays` (`+63d`) or `text` (`63`); count figures accept `count` or `text`. An incompatible formatter is `E_PRESENTATION_SUMMARY_FORMAT`, and a group-only figure is `E_FIGURE_SCOPE_UNAVAILABLE`. Under the approved #1344 omission rule, an undeclared Summary figure omits its metric with `I_SUMMARY_FIGURE_UNBOUND`; a panel with no remaining metrics is omitted. This does not change missing-figure errors for heading or Theme template consumers. The metric `label` is the caption, so a `figures` panel shows the number over it. The `unknown` rule below applies to the other sources only: a declared figure whose fact is missing refuses the render before content is built, so it is never rendered as `unknown`.

## Profile slots and View wording (#1341, #1344)

`source: {slot: <name>}` declares a reusable data slot. Specification06 §9.3
defines View bindings, caption overrides and pointed errors. Binding resolution
precedes Summary figure validation and content measurement. An unbound slot
is omitted with `I_SUMMARY_SLOT_UNBOUND`, not displayed as `unknown` or zero.
Omission preserves the original declaration indexes in surviving completed
SourceRefs, including inline arrangements; omitted metrics emit no primitives.
Info facts carry the original
consumer identity with JSON-safe serialization, without narrowing admitted
panel or metric identifiers. No Project period role or automatic selection is
introduced; the View explicitly selects the project's target.

## Validation and compatibility

A dedicated v0.5 summary-profile schema validates panels and typed metric objects. Legacy mapping values remain accepted as `text` display values. Unknown source or format fails validation; absent typed data is rendered as `unknown` rather than synthesized.

## Ownership

Summary Profile owns metric id, label, source, formatter, and order. Projection and actual-set provide facts. Scene receives resolved text pairs only. This retains the Project / View / Layout / Theme / Scene boundary.

## Plan adjustment

Add the schema and resolver before authoring HALCYON dossier resources; then add unit coverage for `actual.asOf` and planned/count sources.
