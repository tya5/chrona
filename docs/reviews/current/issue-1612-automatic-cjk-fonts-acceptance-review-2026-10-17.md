<!-- chrona:literal-acceptance/v1 -->

# Issue #1612 — automatic CJK font closure

Source `12ca1cc52e16d728b305e3df5663cfd695f20be1`, merged by
[PR #1619](https://github.com/tya5/chrona/pull/1619) as `14820a9e3`; the
measured-source heading/network face-closure correction merged by
[PR #1621](https://github.com/tya5/chrona/pull/1621) as `3d8ab658`.
The exact review-containing main is `8c4d17f917b29600fd72e5b514ad06d31242ca33`
(baseline `6bb56c205`).
[Design, architecture review and implementation plan](https://github.com/tya5/chrona/issues/1612#issuecomment-6225435042).
The exact-main [three-OS release38985610444](https://github.com/tya5/chrona/actions/runs/38985610444)
passed on the final source, including the merged face-closure correction.
Acceptance remains incomplete only because criterion 2's marquee PDF still
has the independently reproduced required-glow refusal; the requested
disposition at [issue comment6225539132](https://github.com/tya5/chrona/issues/1612#issuecomment-6225539132)
is unanswered and no waiver is applied.

## Literal issue acceptance

### Issue #1612

- Source: [Issue #1612](https://github.com/tya5/chrona/issues/1612)
- Observed: 2026-10-17

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | Synthetic test: a Theme naming only a Latin family renders a CJK string through the fallback and records which face it used. | met | [Automatic CJK controls](../../../tests/integration/test_automatic_cjk_fonts.py) cover declared Latin-only Theme, mixed exact face runs, optional provider absent with injected OS faces, info substitution and PDF text/embedded Noto Sans JP program. | — |
| 2 | All 15 presets render a Japanese CSV import to PNG, SVG and PDF with no glyph error, on macOS and on the Linux CI runner (Noto CJK package). View three PNGs and one rasterised PDF. | not met | macOS matrix and [Linux exact-head CI](https://github.com/tya5/chrona/actions/runs/38976260394): 44 successful outputs; marquee PDF retains the independently reproduced required-glow refusal. [Disposition requested](https://github.com/tya5/chrona/issues/1612#issuecomment-6225539132); no waiver applied. Root viewed target-b, Sunday and Marquee PNGs plus rasterized target-b PDF in `/private/tmp/chrona-1612-visual.AI6mTk`. | — |
| 3 | Public SVG/Scene byte-identical for Latin-only examples. | met | Font implementation [artifact12078464991](https://github.com/tya5/chrona/actions/runs/38976260394/artifacts/12078464991) against ready `6bb56c205`: 109 paths each, 0 added/retired; all 50 SVGs and 50 Scenes are byte-identical. Final heading-integration [artifact12082313818](https://github.com/tya5/chrona/actions/runs/38984444157/artifacts/12082313818), based on `0b7ad6558`, adds no font primitives, routes or labels; its six Scene changes are Layout provenance-only. | — |

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
L2+L3=27.6s within60s. The no-provider caption test and covered-caption/info
control added 25 focused passes. [Post-integration audit](https://github.com/tya5/chrona/issues/1612#issuecomment-6226118182)
found that independent headings and native network text dropped measured face
runs; PR #1621 now carries the shared Layout completion correction and
synthetic controls. The exact-main release passed all three full pytest suites,
conformance, wheel-size and installed-wheel smoke, plus MCP-floor and
newest-Python reproduction checks. The release matrix included the 45
preset/target CJK cases with the optional provider installed. This does not
waive the separately recorded marquee PDF refusal.
