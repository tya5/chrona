# Design Correction: View Visual Selector Closure (#350)

**Status:** Complete — blocks completion of I350R-4 target inventory.

## Finding

`view/v0.12` currently declares one permissive target object. Layout ignores
irrelevant selector keys, while `as-of-label` incorrectly requires an `id` even
though the published target model specifies no selector. This admits malformed
authoring documents and leaves the target contract less closed than its Layout
projection.

## Corrected contract

The schema expresses the target vocabulary as a discriminated union. Every
kind has exactly its published selector shape:

| Kind | Required selector | Forbidden extra selector keys |
| --- | --- | --- |
| `title`, `as-of-label` | none | all |
| `column`, `group-header`, `plot-label`, `annotation`, `note-index`, `summary`, `milestone` | `id` | all others |
| `cell` | `object`, `column` | all others |
| `legend` | `role` | all others |
| `axis-label` | `level`, `index` | all others |
| `mark` | `object`, `facet` | all others |

`as-of-label` resolves the sole `as-of-label` placement, not a fabricated
`as-of:{id}` family. A target whose placement is absent on the chosen surface
continues to reject in Layout; the schema never pretends it exists. Encoding
remains admitted only for `cell`, `plot-label`, and `mark` and is rejected by
the schema for every other kind.

## Architecture review

This is a View-boundary correction only. It neither moves selection into
Layout nor creates a generic selector interpreter: View validates the closed
request shape, Layout maps the typed request to its completed placement, and
Scene remains unaware of selectors. It removes ambiguity before Context asset
resolution and therefore strengthens the published no-dead-door rule.

## Acceptance

I350R-4 must add positive coverage for every target form and negative coverage
for omitted, surplus, and encoding-ineligible selector fields. It must show a
selector-free as-of declaration reaches its placement when present and rejects
when the surface has no as-of label.
