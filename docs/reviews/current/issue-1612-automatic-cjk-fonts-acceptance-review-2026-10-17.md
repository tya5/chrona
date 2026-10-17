<!-- chrona:literal-acceptance/v1 -->

# Issue #1612 — automatic CJK font closure

Source `12ca1cc52e16d728b305e3df5663cfd695f20be1`; font closure merged by [PR #1619](https://github.com/tya5/chrona/pull/1619) as `14820a9e3`, and heading/network face closure by [PR #1621](https://github.com/tya5/chrona/pull/1621) as `3d8ab658`. PDF completion merged as `315b9b32b84b8769926a8b751bdef99b1d935f22` in [PR #1635](https://github.com/tya5/chrona/pull/1635), head `9f4640c9e783e5bcea5eb55ee4969b614cd842ca`, based on ready main `fa262ebab648229138eb34c33bf6a821f6450e96`. See the [approved design and plan](https://github.com/tya5/chrona/issues/1612#issuecomment-6225435042) and [PDF glow work record](https://github.com/tya5/chrona/blob/9f4640c9e783e5bcea5eb55ee4969b614cd842ca/docs/planning/active/issue-1612-pdf-glow-work-record-2026-10-17.md). All four literal criteria are met. The issue remains open pending the review-containing exact-main three-OS release; no waiver is applied.

## Literal issue acceptance

### Issue #1612

- Source: [Issue #1612](https://github.com/tya5/chrona/issues/1612)
- Observed: 2026-10-17

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | Synthetic test: a Theme naming only a Latin family renders a CJK string through the fallback and records which face it used. | met | [Automatic CJK controls](../../../tests/integration/test_automatic_cjk_fonts.py) cover Latin-only Theme, mixed exact face runs, provider-absent injected OS faces, info substitution and PDF text/embedded Noto Sans JP. | — |
| 2 | All 15 presets render a Japanese CSV import to PNG, SVG and PDF with no glyph error, on macOS and on the Linux CI runner (Noto CJK package). View three PNGs and one rasterised PDF. | met | macOS: [48 focused integration tests](../../../tests/integration/test_automatic_cjk_fonts.py) pass, including all 45 preset/target outputs; three PNGs and one rasterized PDF were viewed. [Exact-head Linux pytest](https://github.com/tya5/chrona/actions/runs/39004437658) passed all three shards (4201, 4195 and 4210 passes), with the CJK provider installed and no preset-target refusal exception. | — |
| 3 | Public SVG/Scene byte-identical for Latin-only examples. | met | Current [artifact 12090094644](https://github.com/tya5/chrona/actions/runs/39004437658/artifacts/12090094644): 109 paths retained, 0 added/retired; all 50 SVGs and 50 Scenes are byte-identical to ready main `fa262ebab648229138eb34c33bf6a821f6450e96`; no primitive or Scene diagnostic changes across all 50 slides. Only diagnostics/inventory and declared-value inventory change; the latter deliberately pins the PDF raster identity. | — |
| 4 | Reviewer: please trace it and fix it in the face-run path, with a synthetic twin of a mixed Latin+CJK string checked for weight in PNG (and the same in PDF). | met | [Mixed-script raster-face controls](https://github.com/tya5/chrona/blob/9f4640c9e783e5bcea5eb55ee4969b614cd842ca/tests/integration/test_mixed_script_raster_faces.py): portable provider-absent and native Hiragino 400/700 twins verify actual Latin crops against exact-weight references; PDF text extracts and maps to embedded 400/700 programs. The native no-projection control fails as expected. | — |

## Programme-level criteria (optional)

Font ingress closes provider/OS metrics and exact files; Layout completes per-glyph faces and advances; Scene projects them; adapters serialize without discovery or measurement. PDF uses private exact-face aliases and halo-only rasterization while retaining vector text/source paint and isolated alpha resources. Shared run positioning preserves inherited aliases; PNG without fallback runs receives the original SVG and unchanged identity. Strict system-font refusal remains unchanged. Specs08/30/37/63 describe the contract; no preset, example, or generated output was edited.

PR #1635 evidence: 34 projector/halo/registry/PDF-advance tests, 61 renderer/font/opacity controls, and 48 CJK integration tests pass; actual PNG/PDF mixed-script controls pass and the no-projection control fails. Root viewed the current three PNGs and rasterized PDF; the Marquee PDF retains 74 glow halos, soft masks, extractable Japanese text, and vector source paint. CI conformance passes. Local schema equivalence reports L2+L3 at 90.8s against the 60s runtime gate; that local timing failure is disclosed, not waived. Exact-head Linux pytest/conformance/MCP/materializer checks passed; the review-containing exact-main three-OS release remains required before closure.
