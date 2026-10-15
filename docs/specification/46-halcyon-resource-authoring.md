# HALCYON-1 resource authoring specification

## Status

Design complete for issue #46. This specification defines reusable authoring contracts for the HALCYON-1 target slides.

## Authoring boundary

All board, sidebar, and dossier slides are expressed by Project, View, Layout Profile, Theme, Detail/Summary profiles, annotations, and declared contexts. The renderer receives no HALCYON-specific slide branches and no hand-drawn final SVG.

## Reused vocabulary

- Review items, rows, and groups follow the generalized mapping introduced by #41.
- Shared or stacked timeline tracks use the existing `track` contract.
- Group headers, indented rows, table cells, two-level time axes, `actual.asOf`, calendar closure shading, legend swatches, and semantic theme roles reuse #42 vocabulary.

## View additions

### Table source facets

A table column source may address a review item facet:

- `planned`: the planned interval.
- `actual`: the actual interval; absent actual data renders the configured missing value.
- `finishDelta`: actual finish minus planned finish.

A column declares its display formatter rather than embedding date strings in a renderer. Supported formatters are `dateRange`, `date`, `signedDays` (`+10d`) and `signedNumber` (`+10`, the same sign without the unit); `missing: in-progress` is the HALCYON value for an unavailable actual finish.

`dateRange` endpoint display and the packaged-preset migration are defined in
[Spec 24 §1.1](24-table-timeline-presentation.md#11-date-range-endpoint-display-1293).

**Plain zero (#1289).** A `signedNumber` or `signedDays` column may declare `zero: plain` (default `signed`): a zero value reads `0` (`0d` for days) instead of `+0` (`+0d`); a non-zero value keeps its sign, and an `onTime` affix still wraps the text. `zero` on a column whose format is not signed is `E_VIEW_COLUMN_ZERO`.

**Cell transform (#1373).** A column may declare `transform: initials` (a closed set; no other value exists, and an unknown one is `E_VIEW_SCHEMA`). The cell then shows the upper-cased first letter or digit of each word of the field text, so `Ana Maria Lopez` reads `AML` and `fw-team` reads `FT`; the transform is applied while the table is normalized, so Layout measures and Scene carries the completed initials. Rules: words split on Unicode whitespace and on hyphens (`-`, U+2010, U+2011); a word's initial is its first letter or digit (leading punctuation is skipped) with the combining marks that follow it, and a word with none adds nothing; the result is NFC; case mapping is the Unicode default of `str.upper`, with no locale tailoring, so the result never depends on the process or document locale; text without word breaks (unspaced CJK) is one word and gives its first character; a single word gives one letter; no cap is placed on the length. A value with no letter or digit (empty, blank, punctuation only) reads as absent: the `missing` text and the `missing` affix apply. A non-text value is `E_VIEW_COLUMN_TRANSFORM`, as is a `transform` on a source that is not a `field` or `title`, or on a format other than `text`. Absent `transform`, the column is byte-identical to before. `transform` is declared on the View column only, not on a Layout `columnStyles` entry, because the shared `common` part is frozen.

**Lane table columns (#1517).** `transform: initials` is also accepted on a `{field}` column of `rows.laneTable.columns` (Spec 38), with the same rule, applied to the field of the lane's first member.

**Per-state affixes (#588).** A column may declare `affixes`, a mapping from a state to `{prefix, suffix}`
(each 1 to 8 characters, literal, no control character, at least one present). The states are `slip`, `onTime`
and `ahead` (a `signedDays` or `signedNumber` value above, at and below zero) and `missing` (an absent value, of any
format); the state is derived from the value, never from the text. The affix wraps the formatted state text, including
the `missing` text, so `format: signedNumber`, `missing: blank` and `affixes: {slip: {suffix: "!"}, missing: {suffix: "?"}}`
read `+10!` and `?`. A `slip`, `onTime` or `ahead` entry on a column whose format is not signed, an unknown state, or a
malformed entry is `E_VIEW_COLUMN_AFFIX` (a schema failure for the shape, a contract failure for the usability and
control characters). Content normalisation composes the cell string once, so column measurement and placement use the
text with its affixes; under `ellipsize-with-source` Layout cuts only the formatted text and keeps the affixes, and
falls back to cutting the whole string when the affixes leave no room for a character beside an ellipsis. Lane
member labels, summary metrics and Detail labels are not table cells and keep their own formatting. A column without
`affixes` renders as before.

### Axis, marker, and calendar configuration

View presentation may configure the axis labels and interval, the `asOf` marker presentation, and calendar closure shading. Project supplies calendar facts and temporal data; a View selects their visual use. A View never embeds individual non-working dates.

### Labels and annotations

`visibility.labels` is normalized from the current boolean form into a structured presentation option while preserving the existing boolean input. Annotation presentation supports a numbered mode with a deterministic reading order. Project annotations retain their semantic target and optional range.

## Typed summary figures

Summary figures address typed review-item metrics, including `actual.asOf`, planned endpoints, and delta counts. A profile owns labels, ordering, and formatter; it does not copy preformatted project values.

## Semantic theme roles

HALCYON resources bind roles for planned, actual, snapshot, delta, as-of, calendar closure, group headers, notes, and numbered annotations. Layout owns geometry; Theme owns visual token values; Scene contains resolved presentation.

## Required evidence

Every context declared by HALCYON `manifest.yaml` must materialize successfully through the public CLI and produce deterministic SVG evidence. Contract and materialization tests are added; full `pytest` execution is delegated by user instruction.

## Error semantics

Invalid facet, formatter, marker, or annotation mode values fail View validation. Missing actual values are data states and render through the configured missing display policy. Unknown themed roles use the existing fallback behavior.

## Compatibility

Existing Views without the additions preserve current rendering. Legacy Settings/Theme contracts remain deleted and are not reinstated.
