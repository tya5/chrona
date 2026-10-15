# Viewer font stack acceptance

<!-- chrona:literal-acceptance/v1 -->

Plan/design/architecture: [living record](https://github.com/tya5/chrona/issues/1512#issuecomment-6183382396).
Source: `0e3bc5d28a12c8923a48f7d690be3e17903fca9d`, based on READY `f09e4ff44`.
Layout completes the existing family-list string; Scene/adapters do not resolve
Theme resources. Measurement/asset identity is unchanged. SVG/Typst keep viewer
alternatives; PDF/TikZ retain the completed first face. PDF subsets collect that
face's characters. Spec30 records the distinction; no schema change is needed.

Focused evidence:50 initial stack/adapter tests,94 viewer-fit/typeset/PDF tests,
24 CFF/CFF2/variable/collection embedding cases PASS. Public materializer
`--check --jobs 4`: all50 slides PASS without authored resource edits.

## Literal issue acceptance

### Issue #1512

- Source: [issue](https://github.com/tya5/chrona/issues/1512)
- Observed: 2026-10-15

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| --- | --- | --- | --- | --- |
| 1 | Synthetic test: a Theme list `A, B, sans-serif`, with A resolved, writes `font-family="A, B, sans-serif"` in SVG. | met | [Layout cases](../../../tests/unit/chrona/presentation/layout/test_viewer_font_stack.py) and [actual SVG integration](../../../tests/integration/test_installed_fonts.py) cover selected-first/full-list serialization, later and packaged faces, quotes, and identical bounds/baseline/asset identity. | — |
| 2 | On the branch above, the four Yuya/Title Card slides (HALCYON 22/23, roadmap-yuya/titlecard) differ from main only in `font-family`, now the full list. All other public slides are byte-identical. | met | Read-only materializer overlay uses actual Theme bytes from `designs/cjk-font-fallback-20261015`, never authored example edits. All50 rendered: only family attributes change in roadmap-yuya121, roadmap-titlecard125, HALCYON Yuya142, Titlecard140 text nodes; other46 SVGs byte-identical. All50 Scene primitive geometry/paint/text match after removing only family values. [Recorded verification](https://github.com/tya5/chrona/issues/1512#issuecomment-6183382396). | — |
| 3 | Do not edit `examples/**`. | met | [Source commit](https://github.com/tya5/chrona/commit/0e3bc5d28a12c8923a48f7d690be3e17903fca9d) changes only Layout text completion, PDF subset collection, Spec30 and synthetic tests. Reviewer Theme bytes are read through an in-memory overlay, with materializer outputs in temporary directories. | — |

## Programme-level criteria (optional)

None.

Release acceptance pending: current-head PR checks/snapshot inspection and an
exact review-containing public-main three-OS release are required before closure.
