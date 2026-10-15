# Issue #1553: TikZ font selection follows the Theme family list (work record)

Living record for [#1553](https://github.com/tya5/chrona/issues/1553), part of the #1495/#1534 font rule. Written before code; edited in place.

## 1. Published baseline (read on `fae3498e8`)

1. SVG, PNG, PDF and draft measurement resolve a Theme `fontFamily` list in `presentation/fonts/resolution.py: resolve_theme_font_stacks`: the first family that is declared by the Context or installed, with the face files it selected carried to the renderer as `font_files` (`render_review.py` passes `resolution.font_files` to `renderer_for`). The Scene text carries the selected face name in `TextLayout.family`.
2. The TikZ adapter (`renderers/v05_typeset.py: _tikz_numeric_text`) ignores that closure: it writes `\fontspec[Numbers=...]{<first family name>}`, a fontconfig lookup by name. `V05TikzRenderer` is built without `font_files` (`registry.renderer_for`).
3. In CI (`.github/workflows/typesetter-compile.yml`, `tools/check_typesetter_compile.py: _write_fontconfig`) Tectonic sees only `src/chrona/resources/fonts` through a run-local `FONTCONFIG_FILE`. `Noto Sans` is found there; `Noto Sans JP` lives in the `chrona-fonts-noto-cjk` package directory, so yuya TikZ fails with "cannot find font Noto Sans JP" (run 38726146797: 29 of 32 pass; failures are marquee x2 (expected refusal), titlecard TikZ (#1551) and yuya TikZ (this issue)). Typst takes the same family as a native alternative list and falls back silently, so it compiles but may not draw the selected face.
4. XeTeX/fontspec loads a face by file when given `Path=<dir>/` and the file name; this needs no fontconfig. Measured with Tectonic 0.17.0 on macOS: a `Path=\detokenize{...}` value with `_` and space compiles. The adapter never writes a path with a character that TeX would read before `\detokenize` (backslash, braces, `#`, `%`) or that fontspec's key parser splits (`,`, `=`, `[`, `]`).

## 2. Literal acceptance (copied, with the reviewer's brief)

| # | Row | Basis |
| --- | --- | --- |
| A1 | TikZ font selection uses the first family in the Theme list that the typesetter can load | issue body |
| A2 | The packaged Noto CJK face is named by file path when `chrona-fonts-noto-cjk` is installed | issue body |
| A3 | Otherwise the next installed family is used | issue body |
| A4 | If none can be loaded: a counted refusal that names the family | issue body |
| A5 | The compile matrix reports only the marquee refusals (yuya TikZ compiles; titlecard TikZ stays #1551's) | issue body, run 38726146797 |
| A6 | Unit tests for the order (provider installed -> path; absent -> next installed family; none -> refusal naming the family) using `use_installed_fonts(InstalledFontIndex(...))`; opt-in compile tests mirroring `test_typeset_small_caps_compile.py` | reviewer brief |
| A7 | No example, generated file or board edit; gap rows that mention a TikZ font failure are updated | reviewer brief, AGENTS.md |

## 3. Design

The face set is already decided upstream (rule 1); the adapter only has to name the faces it was given in a way Tectonic loads. So the closure reaches the adapter, and the font is named by file.

| Topic | Decision | Alternative, reverse |
| --- | --- | --- |
| Input | `render_v05_tikz(surface, font_files=None)` and `V05TikzRenderer(font_files)`. `renderer_for` passes the resolved `font_files` (the Context's declared files when no stack needed resolving, like the PNG renderer). `None` (adapter called directly with no closure) keeps today's name-based `\fontspec{Family}`: the pinned unit tests and in-process callers are unchanged. | Making the closure required breaks every direct caller; rejected. |
| Face choice | For each Text, the `TextLayout.family` list is walked in order (generic names such as `sans-serif` are skipped). A name selects the file in `font_files` of that family whose weight is nearest `TextLayout.weight` by the CSS rule `InstalledFontIndex` uses. The first name with a loadable file wins. | |
| Loadable | A single-face `.ttf`/`.otf` (or index 0 of a collection) that exists and whose path has none of the characters in baseline row 4. | A collection face at index > 0 has no fontspec spelling; it is skipped, as if not installed. |
| Emission | `\fontspec[Path=\detokenize{<dir>/}, Numbers=...]{<file>}`. Deterministic for a given machine; as for installed faces on SVG, output that names a file depends on where it is rendered (stated in the module docstring). Weight is now honoured (bold roles pick the bold file); before, the family name alone gave regular. | Name-only plus a wider fontconfig directory would fix CI only and leave a macOS/Windows render unable to find the face. |
| Refusal | No name in the list is loadable: `E_VISUAL_CAPABILITY_UNSUPPORTED` (existing family, same code as the other TikZ refusals) with the family list and the reason, so it is counted by the existing refusal accounting (`export_error` in the matrix). No new code, so no inventory change. | A new code would need inventory rules for nothing. |
| Typst | Unchanged: the native alternative list, resolved by Typst from `--font-path`. Out of scope; recorded as a baseline difference. | |
| Layers | Resolution stays in `presentation/fonts`; the adapter serializes a decided face. Change is confined to the font helpers, `render_v05_tikz` Text branch and `V05TikzRenderer`; rotation (#1552) and texture (#1551) lines are not touched. | |

## 4. Evidence required

Unit tests for A1-A4 (in-process font index, no host fonts); opt-in compile test of a synthetic Noto Sans JP run with Tectonic (A2) and a yuya halcyon-1 export before/after compile; the full local pytest set; `regenerate_public_examples --check`; a dispatch of `typesetter-compile.yml` on the branch (A5).

## 5. Progress

Implemented as designed. Measured (Tectonic 0.17.0, halcyon-1, yuya, fontconfig limited to `resources/fonts` as in CI): before, XeTeX halts on the missing `Noto Sans JP`; after, the slide compiles (87 fontspec runs name `noto-sans-jp-{regular,bold}-v1.ttf` by `Path=`) and the PDF was rasterised and read. Local: 9959 passed, 12 skipped (`-m "not corpus"` set); public materializers PASS (50 slides). Not run here: Linux Tectonic (the workflow does it), titlecard TikZ (#1551).
