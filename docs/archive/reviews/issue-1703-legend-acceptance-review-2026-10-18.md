<!-- chrona:literal-acceptance/v1 -->

# Acceptance Review — Realized Legend Keys

Implementation is merged in PR1712 at `3d915fbc9`; exact-main
`96bdfbb7cc2869782905dbc7626ddfdc03f2ef5f` passed native three-OS full release
[39119120797](https://github.com/tya5/chrona/actions/runs/39119120797): Linux
13,563, macOS 13,568, and Windows 13,560 tests passed, as did conformance,
platform probes, wheel build/smoke, newest-Python public reproduction, and the
MCP floor. Earlier pending/failed release notes are superseded by this run.

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
distinct paint, and a pointed warning for colliding meanings. Trial-6 counts,
Scenes, and inspected PNGs are published in the evidence bundle above. All
three literal criteria and the exact-main release gate are met; issue #1703 is
closed.

Boundary review: Layout owns completed key geometry, final filtering and
ambiguity diagnostics. Canonical local geometry and the shared paint resolver
match Scene emission under Spec28 without invented paint or fallback behavior;
Scene/adapters do not acquire placement responsibilities. PR1713 repaired only
the retired-fixture test path; its official 109-file artifact had zero payload
changes. The subsequent exact-main run above passed all release gates.
