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

Implementation candidate: `f24a68430`; reviewer correction [1705](https://github.com/tya5/chrona/pull/1705) restores owner-approved target-b Actual ink. The focused suite previously passed (287 tests, 18.21 s); the Detail validator passed 2 positive and 8 negative cases. Schema equivalence passed for L1 (1 additive, 40 equal) and L2/L3; five pre-existing invalid documents were reported. PR/main publication, the official snapshot and full three-OS release remain unverified. Issue #1703 remains open.

The additional approved equal-figure warning is **not met yet** on restored
target-b: fresh before/after renders have304 primitives and identical PNG/Scene,
but no collision warning despite equal black Actual/Gate diamonds. Runtime
signatures prove translated float32 outline noise causes false inequality.
Spec28 now requires an internal canonical completed local-geometry witness;
independent architecture review confirms Layout ownership, unchanged paint and
passive Scene. Implement the shared point-key witness, then native synthetic
translation/footprint regression and this one-case rerender before acceptance.

| trial-6 case | Scene primitives before → after | Added / removed / changed | Warning count before → after | Observed key result |
| --- | ---: | ---: | ---: | --- |
| `compare-targetb` | 304 → 304 | 0 / 0 / 0 | unchanged | Restored owner-approved Actual/Gate ink `#101828`; their expected collision warning is missing (not accepted). |
| `forecast-tp-deadlines` | 299 → 303 | 4 / 0 / 0 | 29 → 29 | Adds Baseline and Deadline swatch/label pairs; existing forecast `W_DEADLINE` remains, with no new warning code or duplicate-label warning. |
| `starter` | 68 → 68 | 0 / 0 / 0 | 2 → 2 | One ACTUAL key; no duplicate-label warning. |

The native synthetic tests exercise emitted paint equality rather than inventing a color: equal glyph-and-paint meanings retain their faithful swatches and produce the pointed collision diagnostic; distinct realized paints produce distinct swatches. Layout owns the completed key candidates, final filtering, and duplicate/collision diagnostics; Scene and SVG serialize those completed results. No Scene-only result is used as proof of the three user-visible PNGs.
