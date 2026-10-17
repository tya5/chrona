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
The [PDF completion work record](../../planning/active/issue-1612-pdf-glow-work-record-2026-10-17.md)
now implements the published Specs08/63 design without a waiver. macOS passes
all45 outputs; Linux exact-head CI, post1623 public byte comparison and the new
review-containing main release remain pending. Earlier release evidence proves
the font slice, not this PDF completion.

## Literal issue acceptance

### Issue #1612

- Source: [Issue #1612](https://github.com/tya5/chrona/issues/1612)
- Observed: 2026-10-17

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | Synthetic test: a Theme naming only a Latin family renders a CJK string through the fallback and records which face it used. | met | [Automatic CJK controls](../../../tests/integration/test_automatic_cjk_fonts.py) cover declared Latin-only Theme, mixed exact face runs, optional provider absent with injected OS faces, info substitution and PDF text/embedded Noto Sans JP program. | — |
| 2 | All 15 presets render a Japanese CSV import to PNG, SVG and PDF with no glyph error, on macOS and on the Linux CI runner (Noto CJK package). View three PNGs and one rasterised PDF. | not met | Current macOS integration run:48passed, including all45 real outputs; no refusal exception. Root viewed default/executive/Marquee PNGs and rasterized Marquee PDF in `/tmp/chrona-1612-final-visual.aSJfqb`:74glows/74alpha images/74soft masks, Japanese text extractable and source vectors retained. Linux exact-head evidence pending. | — |
| 3 | Public SVG/Scene byte-identical for Latin-only examples. | not met | Published font evidence: [artifact12078464991](https://github.com/tya5/chrona/actions/runs/38976260394/artifacts/12078464991) has all50SVG/50Scene byte-identical; [heading artifact12082313818](https://github.com/tya5/chrona/actions/runs/38984444157/artifacts/12082313818) has no font geometry change. Repeat against the post1623 ready base for the current PDF completion; prior placement changes must not be attributed to this adapter slice. | — |
| 4 | Reviewer: please trace it and fix it in the face-run path, with a synthetic twin of a mixed Latin+CJK string checked for weight in PNG (and the same in PDF). | not met | [Required mixed-script PNG weight finding](https://github.com/tya5/chrona/issues/1612#issuecomment-6229304765). Reproduction and exact-face/full-output controls are pending; the45-output success does not prove this criterion. | — |

## Architecture and current verification

Font ingress closes provider/OS metrics and exact files. Layout completes
per-glyph faces and advances; Scene projects them; adapters serialize without
font discovery or measurement. PDF-private aliases preserve exact assets even
when names/weights coincide, default SVG namespaces and clipping remain intact,
and TikZ uses closed file paths. Strict system-font refusal is unchanged.
Specs08/30/37/63 describe the contract. PDF-only halo lowering consumes completed
regions and original native faces; it retains vector source paint, exact-face
text and isolated Form resources. No preset, example or generated-output edits.
Current focused evidence:76profile/closure,196schema/package,59existing PDF,
37glow/registry/native-face/opacity and48CJK integration tests pass.
L1 schema equivalence:added1/delta3/equal35, frozen v0.1 unchanged.
Full current-source release and public-output identity remain pending.
