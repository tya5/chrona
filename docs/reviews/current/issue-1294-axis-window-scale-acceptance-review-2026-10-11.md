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

Release pending: refreshed exact-head artifacts/PR gates and acceptance-containing
exact-main three-OS release. Local rows do not authorize closure.

Base: trusted READY `95b2fddc` ([gate38108591778](https://github.com/tya5/chrona/actions/runs/38108591778)).
Schema equivalence:38 equal schemas,482 documents/739 probes; four known invalid
fixtures unchanged, L2+L3=37.3s. No schema changes in the CI repair.

[PR1399 first run38109100024](https://github.com/tya5/chrona/actions/runs/38109100024)
failed11 tests across all three shards. [Repair design and failure disposition](https://github.com/tya5/chrona/issues/1294#issuecomment-6105259331):
restore Technical Print's declared patterned month band; preserve old two-band
size fixtures explicitly; update superseded fixed-label and selective-thinning
assertions to published Spec39. Fixed/start-aligned inset coverage remains in
its explicit synthetic fixture. No adapter capability check is weakened.

Repair focused suite:103 passed (42.84s), covering diagnostics, Scene outcomes,
derived sizes, band geometry, packaged declarations and default window scales.
Band checker mutation tests:13 passed (3.77s), including two contiguous lanes
and rejected lane gaps/overlaps. Actual Technical Print SVG/PNG/copy and both
typesetter-capability checks:3 passed (20.92s). PNG sampling follows the actual
Scene band instead of an obsolete fixed coordinate; expected ink/substrate
colors and PNG/SVG raster byte equality are retained.
An earlier batch completed6 tests (both HALCYON CLI viewports, catalogue
contract/render, missing-asset rejection and default preset render) before a
fixed-coordinate PNG assertion failed; it was stopped, not counted as a
successful whole-suite run. Mission/Technical HALCYON checks and refreshed CI
evidence remain pending.
First-head artifact11690588178 had all46 Scene and46 SVG bytes identical;
it is not evidence for the repair head.

## Architecture conclusion

View declares existing permitted units/forms; Theme owns typography. Layout measures natural interval fit, selects the smallest phase-zero regular stride and first viable declared unit, then applies hard host/plot containment. Omission preserves truthful fit/reason facts. Scene/adapters only project completed placements. Fixed visible-overflow remains explicit; no day/week form or weekend-shading expansion is claimed.
