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

Prepared integration `da37f3919` follows ready main `b12cbd7b4` and combines
independently reviewed1701 rows1/2. Legend focus36 and combined date/legend/native64
pass; row2's separate native18 and point/path/style159 batches pass. The
[1701 review](issue-1701-hierarchy-acceptance-review-2026-10-18.md) records its
public15-preset PNG evidence. The published batching amendment retains both
literal reviews and current-head artifact/exact-main full release gates.
The final ready-base hierarchy/legend/native batch passes66; schema-equivalence,
import-direction and literal-review checks pass without new waivers.

Implementation candidate: `192129bd9`; reviewer correction [1705](https://github.com/tya5/chrona/pull/1705) restores owner-approved target-b Actual ink. Final integrated focused tests pass290 (18.03 s), including the native equal-black multipart keys and exact placed-geometry parity. Detail validation passes2 positive/8 negative; schema equivalence passes L1 (1 additive,40 equal) and L2/L3 with five pre-existing invalid documents. PR/main publication, official snapshot and full three-OS release remain unverified. Issue #1703 remains open.

Design correction `6888d036f` precedes repair `192129bd9`: Spec28 and independent
whole-architecture review require the canonical completed local-geometry witness,
not tolerance tuning over translated float32 contours. Native/unit regressions
verify translation/footprint invariance, distinct paints and byte-identical placed
geometry. Combined candidate `e7243add0` was re-rendered against ready main
`5fe41db8e` using unchanged public trial inputs, actual-week2 and baseline.
Root inspected all three native PNGs. Target-b retains faithful black Actual/
Gate swatches and adds exactly one pointed collision warning naming both;
its30 Task cells now show the intended parent/leaf path. Two other cells have
only approximately5e-14 inline-coordinate rounding changes. No viewport override
or Project-data adaptation was used. Commands are `chrona render plan.yaml
--actual actual-week2.yaml --snapshot baseline.yaml --preset target-b`, the
same with `--forecast --preset technical-print --view tp-deadlines-view.yaml`,
and `chrona render starter/project.yaml --actual starter/actual.yaml`, each with
`--output <png> --emit-scene <json>`.
PNG SHA256: target-b `06d1968e6c5ad42253982b51941859719209bec598685b09c116f3efeb47a71d`,
technical-print `9191128c13db036047c7359c7c3d1518a69aaa4e9ae5f6cd9ffa227925a14206`,
starter `322886a53e42153f69bad90c48bb5ddeb0636b22c1f58675e53b032d1cb5ee83`.

| trial-6 case | Scene primitives before → after | Added / removed / changed | Scene diagnostics before → after | Observed key result |
| --- | ---: | ---: | ---: | --- |
| `compare-targetb` | 304 → 304 | 0 / 0 / 32 | 29 → 30 | Owner-approved Actual/Gate ink `#101828` retained; one collision warning;30 path names plus two inline rounding differences. |
| `forecast-tp-deadlines` | 299 → 303 | 4 / 0 / 0 | 29 → 29 | Adds Baseline and Deadline swatch/label pairs; existing forecast `W_DEADLINE` remains, with no new warning code or duplicate-label warning. |
| `starter` | 68 → 68 | 0 / 0 / 0 | 2 → 2 | One ACTUAL key; no duplicate-label warning. |

The native synthetic tests exercise emitted paint equality rather than inventing a color: equal glyph-and-paint meanings retain their faithful swatches and produce the pointed collision diagnostic; distinct realized paints produce distinct swatches. Layout owns the completed key candidates, final filtering, and duplicate/collision diagnostics; Scene and SVG serialize those completed results. No Scene-only result is used as proof of the three user-visible PNGs.
