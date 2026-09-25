# Design — Packaged Monospace Metrics Catalog (#410)

**Design plan:** `issue-410-packaged-monospace-design-plan-2026-09-26.md`.

## Decision

Chrona replaces the single Layout `FontMetrics` input with an immutable
`FontMetricsCatalog`.  The catalog is an identity-pinned mapping from the
exact first family in a resolved Theme font stack and declared weight to one
validated v3 `FontMetrics` asset.  It exposes only:

```python
catalog.select(family: str, weight: int) -> FontMetrics
```

Selection is made in Layout immediately after resolving a `TextTreatment` and
before any transform, wrapping, ellipsis, collision, baseline, or occupied
bound calculation.  `place_text` receives the selected metric, records its
identity, and no later layer reselects it.

The primary package adds Noto Sans Mono Regular (400), its OFL notice, and an
imported declared-metrics-v3 JSON document.  It is a functional face for
identifiers and fixed-width text, not a substitute for numeric spacing: the
existing semantic `numeric` role continues to use Noto Sans tabular figures.

## Authority and data model

| Stage | Authority | Output |
| --- | --- | --- |
| Context font descriptor | Declares every asset with family, weight, byte identity, and metrics identity. | closed resource set |
| Closure | Validates each asset and constructs `FontMetricsCatalog`. | immutable catalog |
| Theme | Chooses a finite family stack and weight by semantic role. | `TextTreatment` |
| Layout | Selects the exact catalog member and measures canonical painted text. | completed placement and asset identity |
| Scene | Carries the completed family, weight, content, geometry, and identity. | renderer-neutral primitive |
| Adapter | Registers all declared files and serializes only the supplied family/weight. | artifact |

`FontMetricsCatalog.select` accepts no fuzzy matching.  The first family in a
Theme stack is the selected family; trailing generic family names are paint
syntax only and cannot become a measurement fallback.  A missing selected
family/weight is `E_FONT_METRICS_UNAVAILABLE` at the resource/Layout boundary.
It is not a renderer fallback and it is not the existing per-glyph substitute
policy.  Glyph substitution remains limited to the declared `missingFont`
policy after a selected face has been established.

## Geometry contract

Every helper that measures text receives the role-selected metric: source
measurement, tables, labels, annotations, legends, axis labels, relation
labels, network labels, wrapping, and ellipsis.  The resulting
`TextPlacement.font_asset_identity` is the selected metric document identity.
The family and weight sent to Scene match that same selection.

Raster adapters register the whole closed Context font-file set but do not
choose among it; their SVG input supplies the selected family/weight.  SVG,
PDF, Typst, and TikZ retain their current completed-text contract.  Thus an
adapter may load the catalog's declared assets but cannot measure in one face
and paint another.

## Resource and corpus migration

The current `declared-metrics-v3` descriptor is extended atomically with the
Noto Sans Mono 400 asset and its metrics document.  Its version does not
change because `assets` is already the closed extensible collection; accepting
a Theme-selected second asset is new behavior of the catalog, not a new
resource syntax.  All public Context descriptors that use the packaged default
gain this identical declared entry in one materializable migration.

One HALCYON Theme defines a `monospace` token and applies it to an existing
semantic role whose public output includes fixed-width identifiers.  This is a
deliberate evidence use, not a new View font-selection field.  Regenerated
Scene/SVG evidence must show the family and a new asset identity; visual review
must confirm the expected fixed-width treatment only where selected.

## Exclusions

- No arbitrary Theme-supplied file, system font, or browser/host fallback.
- No per-column or adapter font selector.
- No automatic conversion of numeric values to monospace.
- No compatibility path that silently measures a missing selected family with
  the previous default metric.

## Acceptance

1. A selected Noto Sans Mono role measures with its own v3 asset and paints
   with that family on every target.
2. A selected but undeclared family/weight fails before Scene generation; a
   target cannot repair it.
3. Existing Noto Sans output retains its selected identity and geometry.
4. Public Contexts, materializers, wheel inclusion/size gate, installed-wheel
   smoke, generated artifacts, full test suite, and three-platform CI prove
   reproducibility.
