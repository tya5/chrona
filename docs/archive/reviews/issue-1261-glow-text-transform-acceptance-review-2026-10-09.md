<!-- chrona:literal-acceptance/v1 -->

# Issue #1261 — glow filter coordinate frame

Public base: `510fd5f90bcc057d72e575423ec6e114dfa51837`.
Design/architecture/implementation plan: [Status](https://github.com/tya5/chrona/issues/1261#issuecomment-6071940312).
Layout/Scene completed geometry is unchanged; SVG applies text glow once in an
untransformed parent. Text identity, transform, opacity and viewer-fit facts remain on
the child. No schema, corpus or preset changes. [PR #1262](https://github.com/tya5/chrona/pull/1262)
merged; the issue closed after the exact-main release on
`ab3075e4f3c8cd584db7ddc14ca08eb2f8d925a0` passed.

## Literal issue acceptance

### Issue #1261

- Source: [Issue #1261](https://github.com/tya5/chrona/issues/1261)
- Observed: 2026-10-09

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | A glowing text run with scale 0.5, 0.86 and 1.0: the emitted filter region contains the run's completed bounds plus three times the blur std on each side. | met | [Pipeline scale/filter tests](../../../tests/integration/test_glow_text_transform.py), including Scene bounds, canvas clipping and emitted region; rotated bounds also tested. | — |
| 2 | A rasterised check shows no clipped ink at the end of the run. | met | [Packaged-font raster tests](../../../tests/integration/test_glow_text_transform.py): all opaque final-glyph source pixels survive at each scale. Old main clips 430/430 final-glyph opaque pixels at 0.5 and 756/890 at 0.86; fixed output clips zero. PNGs visually inspected. | — |
| 3 | Non-glow output is byte-identical. | met | [Three pre-fix byte hashes](../../../tests/unit/chrona/presentation/renderers/test_v05_svg.py); [latest-base artifact audit](https://github.com/tya5/chrona/issues/1261#issuecomment-6072721027) proves all 68 Scenes and 67 non-glow SVGs byte-identical. Only Marquee glow SVG and inventory source locations changed. | — |

## Programme-level criteria (optional)

Focused evidence: 96 SVG/Scene/glow/viewer-fit regressions and seven new transform
tests passed; 24 focused tests passed on the reconciled base. Nested viewer-fit
filters, text opacity, textLength and links are covered.
[Exact-head PR CI 37870612334](https://github.com/tya5/chrona/actions/runs/37870612334)
passed all required checks. Artifact `11590542473`: 145 paths, no retirements;
digest `sha256:8b411cab7319ae79d6ea25bf9ae93347ae6eb34ea5cab87aa000d93c7a7cf73a`.
XML inspection confirmed child text attributes/content/transforms unchanged.
[Exact-main release 37873924553](https://github.com/tya5/chrona/actions/runs/37873924553)
passed Ubuntu/Windows/macOS full pytest, conformance and wheel/smoke, MCP-floor
and newest-Python reproduction. [Closing audit](https://github.com/tya5/chrona/issues/1261#issuecomment-6073491773)
records every literal row and the public release. This archive changes no product files.
