<!-- chrona:literal-acceptance/v1 -->

# Issue #1612 — automatic CJK font closure

Source `12ca1cc52e16d728b305e3df5663cfd695f20be1`, merged by
[PR #1619](https://github.com/tya5/chrona/pull/1619) as `14820a9e3`, ready
main `d2d5460e6` (baseline `6bb56c205`).
[Design, architecture review and implementation plan](https://github.com/tya5/chrona/issues/1612#issuecomment-6225435042).
The exact-main [three-OS release](https://github.com/tya5/chrona/actions/runs/38977809325)
passed at `d2d5460e6`. Release is not accepted: the marquee PDF disposition and
measured-source face closure follow-up in [PR #1621](https://github.com/tya5/chrona/pull/1621)
remain open, including its final review-containing main release.

## Literal issue acceptance

### Issue #1612

- Source: [Issue #1612](https://github.com/tya5/chrona/issues/1612)
- Observed: 2026-10-17

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | Synthetic test: a Theme naming only a Latin family renders a CJK string through the fallback and records which face it used. | met | [Automatic CJK controls](../../../tests/integration/test_automatic_cjk_fonts.py) cover declared Latin-only Theme, mixed exact face runs, optional provider absent with injected OS faces, info substitution and PDF text/embedded Noto Sans JP program. | — |
| 2 | All 15 presets render a Japanese CSV import to PNG, SVG and PDF with no glyph error, on macOS and on the Linux CI runner (Noto CJK package). View three PNGs and one rasterised PDF. | not met | macOS matrix and [Linux exact-head CI](https://github.com/tya5/chrona/actions/runs/38976260394): 44 successful outputs; marquee PDF retains the independently reproduced required-glow refusal. [Disposition requested](https://github.com/tya5/chrona/issues/1612#issuecomment-6225539132); no waiver applied. Root viewed target-b, Sunday and Marquee PNGs plus rasterized target-b PDF in `/private/tmp/chrona-1612-visual.AI6mTk`. | — |
| 3 | Public SVG/Scene byte-identical for Latin-only examples. | met | Final source `12ca1cc52` [artifact12078464991](https://github.com/tya5/chrona/actions/runs/38976260394/artifacts/12078464991) against ready `6bb56c205`: 109 paths each, 0 added/retired; all 50 SVG+50 Scene bytes identical, including Japanese examples. Only two diagnostics reports change source-site references. The separately proposed heading correction still requires its own final artifact audit. | — |

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
L2+L3=27.6s within60s. Exact-head CI above passed all checks; the explicit
no-provider caption test and covered-caption/info control added 25 focused
passes. [Post-integration audit](https://github.com/tya5/chrona/issues/1612#issuecomment-6226118182)
found that independent headings and native network text dropped measured face
runs; PR #1621 carries the shared Layout completion correction and synthetic
controls. It is not yet part of the published font implementation.
The release above passed full pytest (Windows 12,527, Linux 12,529, macOS
12,533), conformance, wheel-size and installed-wheel smoke on all three OSes.
Each job installed the optional CJK provider; unfiltered full-suite selection
includes the 45 preset/target cases (no corpus exclusion). Logs report suite
totals rather than individual node results. This does not waive the separately
recorded marquee PDF refusal.
