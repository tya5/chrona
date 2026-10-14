# Compressed backend and closed PDF face review

<!-- chrona:literal-acceptance/v1 -->

[Design/architecture/plan](https://github.com/tya5/chrona/issues/982#issuecomment-6159490436).
Pre-code specifications: c8b0220b/e8506a76. Implementation eb2ba3af.
Root's own-worktree focused backend/scale/CFF/helper/map/registry batch:88 passed.
Actual Typst0.15.1 compiled returned source with system/embedded fonts disabled.
PDFium5.14.0 rasterized actual ReportLab output at4px/point. Natural/compressed
ink widths: Typst102/52px, PDF305/154px; the pixel-edge intervals contain0.5,
baseline-relative origin differences are1/2px. Both PNGs were visually inspected.
The PDF title resource embeds Noto Sans/400, not the former Verdana substitution.
Negative mutations bypassing the closed map or restoring stable registration names
are rejected by the actual PDF face/glyph tests.

Every face uses the existing deterministic embedding helper and render-local map;
content-addressed internal names prevent ReportLab cache substitution. Geometry,
human names, source font bytes and original asset identities remain unchanged.
PDF bytes/adapter identity intentionally change; Scene/SVG/PNG do not. No new
runtime dependency, private font cache mutation, schema or examples edits.
Current-head public snapshot, labeled native compiler CI and containing-review
exact-main three-OS release are still required before closure. The existing
typesetter workflow retains sources, SVGs, PDFs, PNGs and numeric measurements.

## Literal issue acceptance

### Issue #982

- Source: [issue](https://github.com/tya5/chrona/issues/982)
- Observed: 2026-10-14

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| --- | --- | --- | --- | --- |
| 1 | a compile-and-measure test for the Typst source (or the placement emitted in a form Typst accepts) | met | [Actual returned-source compiler/raster test](../../../tests/integration/test_horizontal_scale_backends.py), pinned Typst0.15.1; [existing required labeled compiler job](../../../.github/workflows/typesetter-compile.yml). Local source compiled and measured102/52px. [Spec08](../../specification/08-scene-and-rendering.md) corrects the obsolete placement claim. | — |
| 2 | a verified TikZ node scale or a recorded decision to keep the rejection | met | Retain the approved [585 D4 decision](https://github.com/tya5/chrona/issues/585#issuecomment-5953239899): no unverified node scale. [Existing synthetic rejection test](../../../tests/integration/test_horizontal_scale.py) and Spec08 preserve E_VISUAL_CAPABILITY_UNSUPPORTED. | — |
| 3 | an image check of the PDF route for a compressed text | met | [Actual PDF image/embedded title-font tests](../../../tests/integration/test_horizontal_scale_backends.py): rasterized returned bytes305/154px,2px origin delta; sequential same-family/weight assets retain distinct selected glyphs, and regular/bold faces are distinct. [CFF glyph/index/permissions regressions](../../../tests/integration/test_pdf_cff_installed.py) also pass. | — |

## Programme-level criteria (optional)

None.
