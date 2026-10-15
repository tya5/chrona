# Issue #429: `titlecard` and `yuya` are not registered (work record)

Living record for the last slice of [#429](https://github.com/tya5/chrona/issues/429). Edited in place.

**Public base:** `13f9f44b3` on `main`. Registered: `editorial`, `technical-print`, `marquee`, `sunday`, `target-b`, `muted-executive`, `wallboard-dark`.

## Finding

Both designs were registered as library entries (in place, shared design-default View; `yuya` with `chrona-target-parts` and `chrona-annotation-parts`, `titlecard` with `chrona-target-parts`). They render on a machine that has Hiragino Sans or Yu Gothic, and fail on one that has none. Reproduced locally with an empty installed-font index (`use_installed_fonts(InstalledFontIndex((), files=()))`), the same state as the Linux CI runner:

| Render (`--preset`) | Result with no installed fonts |
| --- | --- |
| `titlecard`, starter project | `E_FONT_GLYPH_UNAVAILABLE` U+7B2C (`第`, the kicker in the Layout `viewDefaults`) |
| `titlecard`, halcyon-1 | same |
| `yuya`, starter project | ok |
| `yuya`, halcyon-1 | `E_FONT_GLYPH_UNAVAILABLE` U+65E5 (`日`, the slip suffix) |

Why no portable fix exists inside a preset entry:

- The Theme font list `Noto Sans JP, Hiragino Sans, Yu Gothic, sans-serif` reaches installed faces and the packaged Latin Noto Sans only. The draft resolver (`presentation/fonts/resolution.py`) declares metrics only from `fonts/default-font-metrics.yaml` (Noto Sans); it never reads the `chrona-fonts-noto-cjk` provider.
- A Noto Sans JP face is packaged (`packages/chrona-fonts-noto-cjk`, OFL) and halcyon-1 reaches it through its Render Context `environment.fontMetrics.assets` (or the `chrona.noto-sans+jp` font set). The preset library schema (`schemas/preset-library-v0.2.schema.yaml`) has members for View, Theme, Color Scheme, Layout, detail profile and `iconCatalogs` only; it has no font-metrics member, so `render --preset` cannot carry the face.

## Decision needed (reviewer/owner)

Needs a packaged CJK face reachable from `render --preset`, with licence review: either a font-metrics/font-set member in the preset-library schema (a schema change, Spec 56 §3.2 and `schema_equivalence`), or draft resolution that falls back to the `chrona-fonts-noto-cjk` provider when installed. Until then no test is weakened and neither preset is a catalogue entry. The reviewer's other answers stand: the kicker `第弐面` stays in the Layout `viewDefaults`; the countdown slot draws nothing with the generic View (#1344) and was not seen to error; `yuya` needs `chrona-annotation-parts` in its entry.

## Separate named gap (when titlecard is registered)

`titlecard` on the TikZ target is refused with `E_VISUAL_CAPABILITY_UNSUPPORTED` (axis label `horizontal_scale=0.8`; TikZ has no verified horizontal text scale). Typst renders. It needs a name-scoped refusal in `tests/integration/test_typeset_presets.py`.
