# Issue 1532: typeset small-caps runs and horizontal text scale (2026-10-15)

Base: `d2992523a` (origin/main). Basis: the reviewer decision of 2026-10-15 on #1532 (binding), reassigned to dev B.
Owner of the code: `src/chrona/presentation/renderers/v05_typeset.py` (the Typst and TikZ adapters only).
No schema, contract, Scene or Layout change: both facts are already in the completed `TextLayout` (`runs`, `horizontal_scale`).

## Acceptance rows

| # | Row (literal) | Basis and rule | Verification |
| --- | --- | --- | --- |
| a1 | Small-caps runs in Typst | A line with `TextLayout.runs` is serialised run by run, each run at the size Layout measured (`#text(size: ..)`). | Unit string checks; compiled with pinned Typst 0.15.1 and the ink measured (opt-in test, `typesetter-compile` workflow). |
| a2 | Small-caps runs in TikZ | The same runs, each as a `\fontsize{..}{..}\selectfont` group inside the node. | Unit string checks; compiled with pinned Tectonic 0.17.0 and the ink measured. |
| a3 | `sunday` exports | `sunday` no longer in `TYPESET_REFUSED`; both targets export and compile. | `test_typeset_presets.py`, compile matrix `tools/check_typesetter_compile.py`. |
| b1 | Typst `scale(x:)` | Already shipped (#585) and verified; unchanged. | `test_horizontal_scale_backends.py` (existing). |
| b2 | TikZ horizontal scale, bounding box exact | `xscale=<s>` on the node, about the node anchor (`base west` at the baseline start, the SVG pivot). Only shipped after the compiled ink ratio and origin are measured like the Typst and PDF routes; the refusal is removed only with that evidence. | New TikZ case in `test_horizontal_scale_backends.py` (Tectonic, opt-in) plus a rotated+scaled composition check. |
| b3 | `titlecard` exports to TikZ | `("titlecard", "tikz")` removed from `TYPESET_REFUSED_TARGET`. | `test_typeset_presets.py`. |
| c | Glow (marquee): keep the refusal, no approximation, no implicit drop | Untouched: `E_VISUAL_CAPABILITY_UNSUPPORTED` is raised by the visual-capability gate before any adapter runs. | `TYPESET_REFUSED == {"marquee"}`, `TYPESET_REFUSED_TARGET` empty; marquee still asserts the refusal on both targets. |
| d | Names shrink to the marquee glow only | As c. | Same test. |
| e | Outputs checked by eye | Compiled locally (Typst 0.15.1 and Tectonic 0.17.0 downloaded to the scratchpad) and viewed; stated in the PR. | PR body. |
| f | Gap records updated | `docs/diagnostics/{sunday,titlecard,marquee}-vocabulary-gaps.md` rows `typeset-export-refused` / `tikz-horizontal-scale-refused`. | Review. |

## Decision recorded (owner item, proceeds on recommendation)

The decision names Typst `smallcaps()` and TikZ `\textsc`. Both render the font's own `smcp` glyphs from lowercase input.
Layout supplies capitals only (`paint_text` upper-cases; `lines` and the runs are already upper-case) and measures the synthetic
rule (a former lowercase letter at `smallCapsScale` x the size). Typst's `smallcaps()` measured 97.1pt against Layout's 91.87pt
for the same string at 20pt/0.8, so the box would not be exact. The runs are therefore serialised at their measured sizes, using the
Typst and TikZ primitives for a size change. This is the same output the SVG route gives, with the bounding box exact.
