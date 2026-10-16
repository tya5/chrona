<!-- chrona:literal-acceptance/v1 -->

# Issue #1612 — automatic CJK font closure

Product source `467221c95`; public baseline `4358e8844`, reconciled with
`6bb56c205` (reviewer example-pin removal and its trusted generated evidence).
[Design, architecture review and implementation plan](https://github.com/tya5/chrona/issues/1612#issuecomment-6225435042).
Release is not accepted: final-head CI, the marquee PDF disposition, final
public byte audit and exact review-containing main three-OS release are pending.

## Literal issue acceptance

### Issue #1612

- Source: [Issue #1612](https://github.com/tya5/chrona/issues/1612)
- Observed: 2026-10-17

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | Synthetic test: a Theme naming only a Latin family renders a CJK string through the fallback and records which face it used. | met | [Automatic CJK controls](../../../tests/integration/test_automatic_cjk_fonts.py) cover declared Latin-only Theme, mixed exact face runs, optional provider absent with injected OS faces, info substitution and PDF text/embedded Noto Sans JP program. | — |
| 2 | All 15 presets render a Japanese CSV import to PNG, SVG and PDF with no glyph error, on macOS and on the Linux CI runner (Noto CJK package). View three PNGs and one rasterised PDF. | not met | Local matrix: 44 render successfully; marquee PDF retains an independently reproduced existing required-glow capability refusal. [Disposition requested](https://github.com/tya5/chrona/issues/1612#issuecomment-6225539132); no waiver applied. Root viewed target-b, Sunday and Marquee PNGs plus rasterized target-b PDF in `/private/tmp/chrona-1612-visual.AI6mTk`. Linux CI remains required. | — |
| 3 | Public SVG/Scene byte-identical for Latin-only examples. | met | Final source e237dd837 [artifact12077958291](https://github.com/tya5/chrona/actions/runs/38974159285/artifacts/12077958291) against ready6bb56c205:109 paths each,0added/retired; all50 SVG+50 Scene raw bytes identical, including Japanese examples. Only two diagnostics reports change existing source-site references. [Direct archive audit](https://github.com/tya5/chrona/pull/1619#issuecomment-6225724086). Final reconciliation refresh remains a release gate. | — |

## Programme-level criteria (optional)

Font ingress closes provider/OS metrics and exact files. Layout completes
per-glyph faces and advances; Scene projects them; adapters serialize without
font discovery or measurement. PDF-private aliases preserve exact assets even
when names/weights coincide, default SVG namespaces and clipping remain intact,
and TikZ uses closed file paths. Strict system-font refusal is unchanged.
Specs08/30/37 and optional Scene run fields describe the contract. No preset,
example or generated-output edits are part of this implementation.
Reconciled focused run:206 passed; separate strict closure/small-caps/viewer-fit
batch:85 passed. Schema equivalence: additive1/equal37;576 documents/739 probes;
L2+L3=27.6s within60s. Final ready-base CI remains required.
