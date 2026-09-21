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

A column declares its display formatter rather than embedding date strings in a renderer. Supported formatters are `dateRange`, `date`, and `signedDays`; `missing: in-progress` is the HALCYON value for an unavailable actual finish.

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