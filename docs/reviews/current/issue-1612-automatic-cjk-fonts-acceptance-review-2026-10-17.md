<!-- chrona:literal-acceptance/v1 -->

# Issue #1612 — automatic CJK font closure

Product source `467221c95`; public baseline `4358e8844`, reconciled with
`9db9de7da` (reviewer example-pin removal).
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
| 3 | Public SVG/Scene byte-identical for Latin-only examples. | not met | Local public regeneration against4358e884 preserves all50 SVG+50 Scene raw bytes (including Japanese examples); only two diagnostic reports change source-site references. Snapshot archive packaging failed because a directory was supplied as its destination; the raw regenerated files were independently compared. Final ready-base CI artifact must confirm the bound. | — |

## Programme-level criteria (optional)

Font ingress closes provider/OS metrics and exact files. Layout completes
per-glyph faces and advances; Scene projects them; adapters serialize without
font discovery or measurement. PDF-private aliases preserve exact assets even
when names/weights coincide, default SVG namespaces and clipping remain intact,
and TikZ uses closed file paths. Strict system-font refusal is unchanged.
Specs08/30/37 and optional Scene run fields describe the contract. No preset,
example or generated-output edits are part of this implementation.
