<!-- chrona:literal-acceptance/v1 -->

# Acceptance Review — Realized Legend Keys

## Literal issue acceptance

### Issue #1703

- Source: [Issue #1703](https://github.com/tya5/chrona/issues/1703)
- Observed: 2026-10-18

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | Synthetic: baseline and deadline marks drawn → both keyed; actual and gate with distinct realized paints → distinct swatches. | met | [Native SVG baseline/deadline keys](../../../tests/integration/test_default_legend_keys_svg.py); [realized-paint collision and distinct-paint coverage](../../../tests/integration/test_legend_ambiguity.py); [native layout diagnostic coverage](../../../tests/unit/chrona/presentation/layout/test_legend_diagnostics.py) | — |
| 2 | Two keys with one label → the warning names both meanings. | met | [Duplicate displayed-label warning names both meanings after final filtering](../../../tests/integration/test_legend_ambiguity.py); [native layout diagnostic coverage](../../../tests/unit/chrona/presentation/layout/test_legend_diagnostics.py) | — |
| 3 | trial-6 PNGs re-rendered, plus a count table. | met | The three public CLI renders and emitted Scenes were reviewed locally from [trial-6 inputs](https://github.com/tya5/chrona/tree/531f5007e/trial-6); before/after counts and PNG evidence are recorded below. The separate official derived snapshot and release gate are pending. | — |

## Programme-level criteria (optional)

### Evidence and release status

Implementation candidate: `ac6e3435bf97bdaa16a6bd064f469a4816b34dae`; reviewer preset source: `b70ed46d1c3ea8cfb6a8a85a858ddc8d7728afe1`. The focused suite passed (287 tests, 18.21 s); the Detail validator passed 2 positive and 8 negative cases. Schema equivalence passed for L1 (1 additive, 40 equal) and L2/L3; five pre-existing invalid documents were reported. This is candidate evidence only: PR/main publication, the official snapshot, and the full three-OS release gate have not been verified. Issue #1703 remains open.

| trial-6 case | Scene primitives before → after | Added / removed / changed | Warning count before → after | Observed key result |
| --- | ---: | ---: | ---: | --- |
| `compare-targetb` | 304 → 304 | 0 / 0 / 0 | 28 → 28 | One Actual key; snapshot/planned/gate keys remain distinct. Actual ink `#1D5FD1`; gate ink `#101828`. |
| `forecast-tp-deadlines` | 299 → 303 | 4 / 0 / 0 | 29 → 29 | Adds Baseline and Deadline swatch/label pairs; existing forecast `W_DEADLINE` remains, with no new warning code or duplicate-label warning. |
| `starter` | 68 → 68 | 0 / 0 / 0 | 2 → 2 | One ACTUAL key; no duplicate-label warning. |

The native synthetic tests exercise emitted paint equality rather than inventing a color: equal glyph-and-paint meanings retain their faithful swatches and produce the pointed collision diagnostic; distinct realized paints produce distinct swatches. Layout owns the completed key candidates, final filtering, and duplicate/collision diagnostics; Scene and SVG serialize those completed results. No Scene-only result is used as proof of the three user-visible PNGs.
