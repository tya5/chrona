<!-- chrona:literal-acceptance/v1 -->

# Acceptance Review — Realized Legend Keys

Implementation is merged in PR1712 at `3d915fbc9`; ready main is
`9e59e3f024171811d45b0f6b7b1f6c89f1587754`. Final PR CI39114476434 passed;
official artifact12132160084 contains109 paths with no retirements, and its
50 SVG/Scene pairs match the reviewed candidate. The exact-main three-OS full
release [39115747584](https://github.com/tya5/chrona/actions/runs/39115747584)
is pending; this review does not claim release acceptance or issue closure.

## Literal issue acceptance

### Issue #1703

- Source: [Issue #1703](https://github.com/tya5/chrona/issues/1703)
- Observed: 2026-10-18

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| --- | --- | --- | --- | --- |
| 1 | Synthetic: baseline and deadline marks drawn → both keyed; actual and gate with distinct realized paints → distinct swatches. | met | [Native SVG baseline/deadline keys](../../../tests/integration/test_default_legend_keys_svg.py); [realized-paint collision and distinct-paint coverage](../../../tests/integration/test_legend_ambiguity.py); [native layout diagnostic coverage](../../../tests/unit/chrona/presentation/layout/test_legend_diagnostics.py) | — |
| 2 | Two keys with one label → the warning names both meanings. | met | [Duplicate displayed-label warning names both meanings after final filtering](../../../tests/integration/test_legend_ambiguity.py); [native layout diagnostic coverage](../../../tests/unit/chrona/presentation/layout/test_legend_diagnostics.py) | — |
| 3 | trial-6 PNGs re-rendered, plus a count table. | met | The [public three-render PNG/Scene evidence and count table](https://github.com/tya5/chrona/blob/1dedf067ba08a603050f129b3b1a4da654c7d943/review-evidence/issue-1703/README.md) records the rerenders from unchanged [trial-6 inputs](https://github.com/tya5/chrona/tree/531f5007e/trial-6); the PNGs were inspected. | — |

## Programme-level criteria (optional)

Design correction `6888d036f` and whole-architecture review preceded code. The
synthetic native tests verify faithful completed paint, distinct swatches for
distinct paint, and a pointed warning for colliding meanings. The public
count-table README is the single source for trial-6 counts and renders; this
review does not duplicate them. All three literal criteria have functional
evidence; exact-main full release remains the sole pending acceptance gate.
