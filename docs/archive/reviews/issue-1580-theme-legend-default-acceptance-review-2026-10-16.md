<!-- chrona:literal-acceptance/v1 -->

# Acceptance Review — Theme Legend Shape Default (#1580)

Released through [PR #1589](https://github.com/tya5/chrona/pull/1589).
Exact review-containing main `6ae0ccd80ed8b7b5e05a0edfbc09d2ef3f9113a1`
passed [three-OS release38820611467](https://github.com/tya5/chrona/actions/runs/38820611467).
Final head `393a16534` passed CI38818663157; artifact12011628134
preserves all 50 SVG and 50 Scene raw bytes, with no added/retired paths.

## Literal issue acceptance

### Issue #1580

- Source: [Issue #1580](https://github.com/tya5/chrona/issues/1580)
- Observed: 2026-10-16
- Plan: [approved comment](https://github.com/tya5/chrona/issues/1580#issuecomment-6203027683)

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | Synthetic tests: Theme default present/absent, Detail override wins, generated scale key takes the default. | met | [Integration](../../../tests/integration/test_legend_swatch_shapes.py), [contract](../../../tests/unit/chrona/presentation/contracts/test_legend_swatch_contract.py), [token](../../../tests/unit/chrona/presentation/model/test_theme_tokens.py) and [capability](../../../tests/unit/chrona/presentation/scene/test_capabilities.py) modules:98 tests pass, including after the d65735f13 reconciliation. Shared measurement/emission, invalid values and derived inheritance are covered. | — |
| 2 | wallboard-dark PNG shows all legend keys as circles. | met | `chrona render examples/halcyon-1/project.yaml --actual examples/halcyon-1/actual.yaml --preset wallboard-dark --format png --output <path>` succeeds. Implementer and root independently viewed all11 circular keys. The [bundled Theme](../../../src/chrona/resources/presets/bundles/wallboard-dark/theme.yaml) declares the default. | — |
| 3 | All public SVG and Scene files are byte-identical (wallboard is not a committed example). | met | At130c84b7f on base7ca7e5553, the [public materializer checker](../../../tools/regenerate_public_examples.py), run as `.venv/bin/python tools/regenerate_public_examples.py --check --jobs 4`, passes all50 slides, comparing all50SVG+50Scene raw bytes. Check mode writes no product files; final PR snapshot and release are separate gates. | — |

## Programme-level criteria (optional)

Schema equivalence passed after retiring merged deltas: L1 delta 1/equal 37; 575 corpus documents, 465 mapped and 5 existing invalid; 739 L3 probes; L2+L3 runtime 43.5s/60s.

## Architecture conclusion

Theme schema admission reuses the existing closed `circle`/`rule-pair` vocabulary; the finite Theme consumer registry assigns the new property to Layout. `ThemeTokenView` reads the optional default, and Layout resolves Detail-over-Theme precedence in `swatch_extent`, shared by measurement and drawing. No Scene or adapter behavior was added. With the Theme property absent, the existing legacy geometry path remains active.

All three literal acceptance rows and the exact-main release gate are met.
