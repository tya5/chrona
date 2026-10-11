<!-- chrona:literal-acceptance/v1 -->

# Default axis window-scale acceptance (#1294)

Implementation: `0064cfaf`, `53d401f6`, `69a917f1`. [Current design and implementation record](https://github.com/tya5/chrona/issues/1294#issuecomment-6094159905); authority: Spec39 section1.1.

## Literal issue acceptance

### Issue #1294

- Source: [Issue #1294](https://github.com/tya5/chrona/issues/1294)
- Observed: 2026-10-11

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | A test over windows of increasing length (one month → ten years) with the default preset. From the Scene, no two axis-label primitives in the same tier intersect, and every thinned tier reports its thinning. | met | [Default Scene/SVG tests](../../../tests/integration/test_default_axis_window_scale.py) resolve the actual library default; cover one month, quarter, year, five years and ten years; assert pairwise same-tier bounds and density for each thinned tier. | — |
| 2 | A tier declared `thin-with-record` never yields `W_LAYOUT_LABEL_OVERFLOW` for its own labels. | met | [Default integration](../../../tests/integration/test_default_axis_window_scale.py) rejects axis-label overflow; [natural typography](../../../tests/unit/chrona/presentation/layout/test_axis_natural_typography.py) and [tier geometry](../../../tests/unit/chrona/presentation/layout/test_surface_axis_tier_geometry.py) cover fit/omission rather than visible-overflow fallback. | — |
| 3 | The five-year case above renders without `W_SCENE_TEXT_INTERSECTION` between axis labels. | met | [Reported task/gate fixture](../../../tests/integration/test_default_axis_window_scale.py) uses issue dates and titles, checks Scene bounds/perceptibility and actual SVG label emission. | — |
| 4 | Do not edit `examples/**`. | met | [Cadence implementation](https://github.com/tya5/chrona/commit/53d401f6): `git diff --name-only origin/main...HEAD -- examples` is empty for the authored WIP. Corpus changes must be disclosed, never patched to pass. | — |

## Programme-level criteria (optional)

Release pending: trusted READY-base integration, fresh public artifacts/current-head PR gates and acceptance-containing exact-main three-OS release. Local rows do not authorize closure.

Related focused suite: 156 passed (13.84s), including regular cadence, natural typography, fixed/automatic tier geometry, lane placement, all nine packaged Views, week forms, explicit fixed-month secondary declarations and band containment. After strengthening per-tier reporting and using exact issue titles, the default suite passed again: six tests (4.54s).

## Architecture conclusion

View declares existing permitted units/forms; Theme owns typography. Layout measures natural interval fit, selects the smallest phase-zero regular stride and first viable declared unit, then applies hard host/plot containment. Omission preserves truthful fit/reason facts. Scene/adapters only project completed placements. Fixed visible-overflow remains explicit; no day/week form or weekend-shading expansion is claimed.
