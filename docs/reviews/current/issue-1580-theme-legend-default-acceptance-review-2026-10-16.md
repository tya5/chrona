<!-- chrona:literal-acceptance/v1 -->

# Acceptance Review — Theme Legend Shape Default (#1580)

**Implementation:** [commit `0182956cc6aafbc5bb8b567f2a349ed958032dd5`](https://github.com/tya5/chrona/commit/0182956cc6aafbc5bb8b567f2a349ed958032dd5), on ready base [`7ca7e5553244b1e726730ad07304c08562cf93d6`](https://github.com/tya5/chrona/commit/7ca7e5553244b1e726730ad07304c08562cf93d6). **Approved plan:** [#1580 implementation/status comment](https://github.com/tya5/chrona/issues/1580#issuecomment-6203027683). **Observed:** 2026-10-16.

## Literal issue acceptance

### Issue #1580

- Source: [Issue #1580](https://github.com/tya5/chrona/issues/1580)
- Observed: 2026-10-16
- Plan: [approved comment](https://github.com/tya5/chrona/issues/1580#issuecomment-6203027683)

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | `[Input]` Synthetic tests: Theme default present/absent, Detail override wins, generated scale key takes the default. | met | [`test_legend_swatch_shapes.py`](../../../tests/integration/test_legend_swatch_shapes.py), [`test_legend_swatch_contract.py`](../../../tests/unit/chrona/presentation/contracts/test_legend_swatch_contract.py), [`test_theme_tokens.py`](../../../tests/unit/chrona/presentation/model/test_theme_tokens.py), and [`test_capabilities.py`](../../../tests/unit/chrona/presentation/scene/test_capabilities.py): focused command `.venv/bin/python -m pytest -q tests/integration/test_legend_swatch_shapes.py tests/unit/chrona/presentation/contracts/test_legend_swatch_contract.py tests/unit/chrona/presentation/model/test_theme_tokens.py tests/unit/chrona/presentation/scene/test_capabilities.py --tb=short` passed, 98 tests. Covers Theme default absent/present, invalid vocabulary, Detail precedence, generated scale keys, and shared measurement/emission extent. | — |
| 2 | `[Input]` wallboard-dark PNG shows all legend keys as circles. | met | Rendered with `.venv/bin/chrona render examples/halcyon-1/project.yaml --actual examples/halcyon-1/actual.yaml --preset wallboard-dark --format png --output /tmp/chrona-1580-wallboard-dark.png`; status `ok`. The [bundled Theme](../../../src/chrona/resources/presets/bundles/wallboard-dark/theme.yaml) sets the circle default. The PNG was visually inspected by the implementer and independently by the root reviewer; all 11 legend keys are circles. | — |
| 3 | `[Input]` All public SVG and Scene files are byte-identical (wallboard is not a committed example). | met | On code revision `130c84b7fb2fb99a4e7f4aff0c243ba23df3d9cc`, layered on ready base [`7ca7e5553244b1e726730ad07304c08562cf93d6`](https://github.com/tya5/chrona/commit/7ca7e5553244b1e726730ad07304c08562cf93d6), [`regenerate_public_examples.py`](../../../tools/regenerate_public_examples.py) ran as `.venv/bin/python tools/regenerate_public_examples.py --check --jobs 4` and passed: 50 slides reproduced with no public artifact diffs (50 SVG and 50 Scene files). Check mode made no product-file writes. | — |

## Programme-level criteria (optional)

Schema equivalence passed after retiring merged deltas: L1 delta 1/equal 37; 575 corpus documents, 465 mapped and 5 existing invalid; 739 L3 probes; L2+L3 runtime 43.5s/60s.

## Architecture conclusion

Theme schema admission reuses the existing closed `circle`/`rule-pair` vocabulary; the finite Theme consumer registry assigns the new property to Layout. `ThemeTokenView` reads the optional default, and Layout resolves Detail-over-Theme precedence in `swatch_extent`, shared by measurement and drawing. No Scene or adapter behavior was added. With the Theme property absent, the existing legacy geometry path remains active.

All three literal acceptance rows are met. The final PR snapshot and release CI remain pending; this review does not claim those publication gates are complete.
