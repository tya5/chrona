# Release Acceptance Review — Packaged Monospace Metrics Catalog (#410)

**Design:** `issue-410-packaged-monospace-catalog-design-2026-09-26.md`.
**Architecture review:**
`issue-410-packaged-monospace-catalog-architecture-review-2026-09-26.md`.
**Implementation plan:**
`issue-410-packaged-monospace-implementation-plan-2026-09-26.md`.

## Decision

Accepted.  #410 is complete.  Its earlier typed treatment and tabular-metrics
releases established measurement-aware transform, tracking, and numeric
spacing.  This release closes the remaining packaged-face requirement with an
immutable exact-face `FontMetricsCatalog` and Noto Sans Mono Regular (400).

## Acceptance mapping

| Requirement | Released evidence | Result |
| --- | --- | --- |
| Layout measures the text it paints | Theme treatment resolves before all Layout measurement; the catalog selects the exact first family and weight, and `TextPlacement` records that metric identity before Scene exists. | Pass |
| A monospace family needs no import step | Primary resources contain the Noto Sans Mono 400 font, OFL notice, and imported v3 metrics asset.  The default descriptor declares their byte and metric identities. | Pass |
| Selection cannot silently fall back | Catalog lookup is exact by first stack family and weight.  Unknown family/weight raises `E_FONT_METRICS_UNAVAILABLE` before Scene; generic trailing families and adapters cannot repair it. | Pass |
| Existing numeric behavior stays semantic | `numeric` remains Noto Sans tabular figures.  HALCYON's `summary` role intentionally selects the new `monospace` token as public fixed-width evidence rather than converting values automatically. | Pass |
| Contexts and targets stay reproducible | Every public Context gained the closed declared asset entry atomically.  Layout supplies family, weight, and identity; adapters register declared bytes but do not select or measure a face. | Pass |
| Default distribution is bounded | The primary wheel is built, budget-checked, force-installed outside the checkout, and smoke-tested in CI. | Pass |

## Verification

- Packaged catalog selection verifies Noto Sans Mono's identity
  `sha256:c886cba7994069f6ba1c1a97c49d3aff58a3c131e6b4710237a452bd67a845a4`;
  unknown family and weight selection remain negative cases.
- The release-focused public materializer, packaged-resource, font-metric, and
  layout checks passed: **30 passed**.
- GitHub Actions run `36159854167` passed full `pytest -n 4`, conformance,
  all structural/coverage gates, wheel budget, and installed-wheel smoke on
  Ubuntu, macOS, and Windows.
- Its Python 3.12 reproduction job regenerated every public materializer
  Context successfully from the public CLI.

## Architecture result

The added face extends the existing closed Context resource set without a new
Theme syntax, system-font dependency, adapter font selector, or numeric
shortcut.  The authority chain remains Context closure → Theme treatment →
Layout metric selection → completed Scene text → adapter serialization.  The
four #410 additions are now complete without a measurement/paint divergence.
