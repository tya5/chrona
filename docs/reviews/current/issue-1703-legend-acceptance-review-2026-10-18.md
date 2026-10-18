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

Prepared integration `163ba8725` follows ready main `381cf404a` and combines
the independently reviewed1701 row1 date correction. Current-main legend
focus36 and combined date/legend/native64 pass. Both issue reviews and required
artifact/full release gates remain in force;1701 row2 is design-only.

Implementation candidate: `192129bd9`; reviewer correction [1705](https://github.com/tya5/chrona/pull/1705) restores owner-approved target-b Actual ink. Final integrated focused tests pass290 (18.03 s), including the native equal-black multipart keys and exact placed-geometry parity. Detail validation passes2 positive/8 negative; schema equivalence passes L1 (1 additive,40 equal) and L2/L3 with five pre-existing invalid documents. PR/main publication, official snapshot and full three-OS release remain unverified. Issue #1703 remains open.

Design correction `6888d036f` precedes repair `192129bd9`: Spec28 and independent
whole-architecture review require the canonical completed local-geometry witness,
not tolerance tuning over translated float32 contours. Native/unit regressions
verify translation/footprint invariance, distinct paints and byte-identical placed
geometry. The repaired target-b render now adds exactly one pointed collision
warning naming `actual (actual)` and `gate (milestone)`; faithful black swatches
remain unchanged. Root inspected the native PNG; its SHA256 is
`c21d5439c20033b2c6f9fb0d625368550feffbf7dec50a4e34d2d9943e510d50`, identical
to the1705 baseline. Scene surfaces are identical; only the expected diagnostic
and CLI warning change (7 warning records,8 occurrences). The command uses the
public trial inputs, actual-week2, baseline and target-b without a viewport
override. The other two cases are unaffected by the target-b-only YAML correction.

| trial-6 case | Scene primitives before → after | Added / removed / changed | Scene diagnostics before → after | Observed key result |
| --- | ---: | ---: | ---: | --- |
| `compare-targetb` | 304 → 304 | 0 / 0 / 0 | 29 → 30 | Restored owner-approved Actual/Gate ink `#101828`; adds one collision warning naming both meanings. PNG and full surface payload unchanged. |
| `forecast-tp-deadlines` | 299 → 303 | 4 / 0 / 0 | 29 → 29 | Adds Baseline and Deadline swatch/label pairs; existing forecast `W_DEADLINE` remains, with no new warning code or duplicate-label warning. |
| `starter` | 68 → 68 | 0 / 0 / 0 | 2 → 2 | One ACTUAL key; no duplicate-label warning. |

The native synthetic tests exercise emitted paint equality rather than inventing a color: equal glyph-and-paint meanings retain their faithful swatches and produce the pointed collision diagnostic; distinct realized paints produce distinct swatches. Layout owns the completed key candidates, final filtering, and duplicate/collision diagnostics; Scene and SVG serialize those completed results. No Scene-only result is used as proof of the three user-visible PNGs.
