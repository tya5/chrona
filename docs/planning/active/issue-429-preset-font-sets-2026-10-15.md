# Issue #429: a preset declares the font set it needs (work record)

Living record. Public base: `85c4d8aa7` on `main`. Refs #429. Decision: option 1 of the 2026-10-15 question on #429 (a font-set member), kept by the reviewer, whose post-merge decision on #1527 changed the failure mode (below).

## Problem

`titlecard` and `yuya` render on a machine with a CJK face but fail with `E_FONT_GLYPH_UNAVAILABLE` (`第`, `日`) on one without. The packaged Noto Sans JP exists (`packages/chrona-fonts-noto-cjk`, OFL) and `fontMetrics.fontSet: chrona.noto-sans+jp` of a Render Context reaches it, but a draft render builds its font descriptor from the packaged default (Latin only) or from `--font-metrics`, and a preset cannot name a set.

## How the pieces connect today

- `resources/fonts/font-sets.yaml` maps a set id to an exact asset list; `contracts/font_sets.expand_font_set` expands a Context's `fontSet` (Render Context schema enum: `chrona.noto-sans`, `chrona.noto-sans+jp`).
- The `+jp` assets use `provider: package, identity: chrona-fonts-noto-cjk`, resolved by `font_resources._package_root` through the `chrona.font-resource-provider` entry point. Not installed: `E_FONT_METRICS_UNAVAILABLE` (a loud, named failure).
- A draft render: `resolve_draft_render` -> `_draft_render_from_resources(font_metrics=...)`; `None` means the packaged descriptor. `resolve_theme_font_stacks` then adds installed faces behind the declared ones.
- `render --preset <id>` and `preset copy <id>` both go through `copy_builtin_preset` (draft_render.py materializes a temp copy), so whatever `preset.yaml` carries reaches the draft path.

## Failure mode: a font set adds candidates (reviewer decision, post-#1527)

`chrona-fonts-noto-cjk` is not a dependency or extra of the `chrona` wheel; AGENTS.md setup and CI install it. The first version of #1527 made a declared set a hard requirement: on a plain `pip install chrona` with a CJK face installed (macOS Hiragino), `render --preset titlecard|yuya` was rejected with `E_FONT_METRICS_UNAVAILABLE ... provider unavailable`, though the same machine rendered them before #1527 through the Theme family list (#1495 + #1524). Installed fonts are a normal source and reproducibility is not a goal, so the rule is now:

- A declared set adds candidates. When its package provider is not installed, the set's assets are skipped with the existing `W_FONT_FAMILY_SKIPPED` (`role=font-set;requested=<set>;skipped=<provider>`), and the Theme family list continues on installed fonts as #1495 does.
- `E_FONT_GLYPH_UNAVAILABLE` remains only when a glyph is still missing after that (font-poor Linux without the package).
- Provider present: unchanged.
- The Render Context path is not softened: its `fontMetrics` (assets or `fontSet`) is the declared closure of an immutable render, so a missing provider there stays `E_FONT_METRICS_UNAVAILABLE`. The guided-authoring path does not read `fontSets` (unchanged).
- No `chrona[cjk]` extra for now; revisit at release packaging.

## Design

1. `preset-library-v0.2`: `members.fontSets`, an optional array (unique items, min 1) of font-set ids, enum `[chrona.noto-sans, chrona.noto-sans+jp]` (the Render Context's names). Additive; absent means today's behaviour.
2. `presentation-preset-v0.1`: `body.resources.fontSets`, the same optional array, so a copied preset carries it (the spec already says the v0.1 preset takes optional pins; this is one more, optional, no version bump).
3. `copy_builtin_preset` writes the declaration into `preset.yaml`. No font file is copied: a set is a name for packaged, identity-pinned assets, like `fontSet` in a Context. A user's copy keeps the declaration; deleting the line returns to the Latin default.
4. `contracts/font_sets.draft_font_metrics(set_ids, base_descriptor)` builds the descriptor: the base descriptor header (`algorithm`, `missingFont`) with the union of the named sets' assets, deduplicated by (family, weight), in declared order.
4a. `draft_font_metrics(..., unavailable)` leaves out assets of a provider that is not installed (probed in `closure._preset_font_metrics`), which also yields the `W_FONT_FAMILY_SKIPPED` note (message branch in `diagnostic_messages`; no new code, so no inventory change).
5. `resolve_draft_render`: an explicit `--font-metrics` wins; else the preset's `fontSets` build the descriptor; else the packaged default. Installed faces remain a fallback behind it (#1281), unchanged.

## Not changed

Render Context schema, closure identity of immutable renders, design YAML, `examples/**`. A preset without `fontSets` renders byte-identically.

## Tests

Schema accepts/refuses; loader copies the declaration; draft render with the declaration renders `第`/`日` under `use_installed_fonts(InstalledFontIndex((), files=()))`, and the same preset without it refuses with `E_FONT_GLYPH_UNAVAILABLE`; explicit `--font-metrics` wins; provider missing: an installed CJK face renders with `W_FONT_FAMILY_SKIPPED`, no face gives `E_FONT_GLYPH_UNAVAILABLE`, provider present is unchanged; then `titlecard` and `yuya` registered with the declaration (entries from `8ebabcdb1`, name-scoped TikZ refusal for titlecard).
