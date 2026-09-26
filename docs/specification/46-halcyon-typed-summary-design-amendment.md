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

## Validation and compatibility

A dedicated v0.5 summary-profile schema validates panels and typed metric objects. Legacy mapping values remain accepted as `text` display values. Unknown source or format fails validation; absent typed data is rendered as `unknown` rather than synthesized.

## Ownership

Summary Profile owns metric id, label, source, formatter, and order. Projection and actual-set provide facts. Scene receives resolved text pairs only. This retains the Project / View / Layout / Theme / Scene boundary.

## Plan adjustment

Add the schema and resolver before authoring HALCYON dossier resources; then add unit coverage for `actual.asOf` and planned/count sources.
