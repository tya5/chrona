# Issue #429: a preset declares the font set it needs (work record)

Living record. Public base: `85c4d8aa7` on `main`. Refs #429. Decision taken: option 1 of the 2026-10-15 question on #429 (a font-set member), on the author's recommendation until the reviewer answers otherwise.

## Problem

`titlecard` and `yuya` render on a machine with a CJK face but fail with `E_FONT_GLYPH_UNAVAILABLE` (`第`, `日`) on one without. The packaged Noto Sans JP exists (`packages/chrona-fonts-noto-cjk`, OFL) and `fontMetrics.fontSet: chrona.noto-sans+jp` of a Render Context reaches it, but a draft render builds its font descriptor from the packaged default (Latin only) or from `--font-metrics`, and a preset cannot name a set.

## How the pieces connect today

- `resources/fonts/font-sets.yaml` maps a set id to an exact asset list; `contracts/font_sets.expand_font_set` expands a Context's `fontSet` (Render Context schema enum: `chrona.noto-sans`, `chrona.noto-sans+jp`).
- The `+jp` assets use `provider: package, identity: chrona-fonts-noto-cjk`, resolved by `font_resources._package_root` through the `chrona.font-resource-provider` entry point. Not installed: `E_FONT_METRICS_UNAVAILABLE` (a loud, named failure).
- A draft render: `resolve_draft_render` -> `_draft_render_from_resources(font_metrics=...)`; `None` means the packaged descriptor. `resolve_theme_font_stacks` then adds installed faces behind the declared ones.
- `render --preset <id>` and `preset copy <id>` both go through `copy_builtin_preset` (draft_render.py materializes a temp copy), so whatever `preset.yaml` carries reaches the draft path.

## Dependency fact (owner-relevant)

`chrona-fonts-noto-cjk` is **not** a dependency of the `chrona` wheel (`pyproject.toml` dependencies: PyYAML, jsonschema, fonttools, skia-pathops) and not an extra. It is a separate package installed explicitly: AGENTS.md setup and every CI workflow (`conformance.yml`, `typesetter-compile.yml`, `derived-*.yml`, `test-durations.yml`) install `-e packages/chrona-fonts-noto-cjk`. Consequence:

- In CI and in the documented developer setup, a preset that declares `chrona.noto-sans+jp` renders everywhere, including a machine with no installed CJK face.
- On a plain `pip install chrona` (no CJK package), `chrona preset list` still lists `titlecard` and `yuya`, and rendering one fails loudly with `E_FONT_METRICS_UNAVAILABLE` naming the missing provider `chrona-fonts-noto-cjk`. It never substitutes silently. Making them render there needs the package to become a dependency or an extra of the wheel: **an owner decision, not made here.** Recorded as the question on #429.

## Design

1. `preset-library-v0.2`: `members.fontSets`, an optional array (unique items, min 1) of font-set ids, enum `[chrona.noto-sans, chrona.noto-sans+jp]` (the Render Context's names). Additive; absent means today's behaviour.
2. `presentation-preset-v0.1`: `body.resources.fontSets`, the same optional array, so a copied preset carries it (the spec already says the v0.1 preset takes optional pins; this is one more, optional, no version bump).
3. `copy_builtin_preset` writes the declaration into `preset.yaml`. No font file is copied: a set is a name for packaged, identity-pinned assets, like `fontSet` in a Context. A user's copy keeps the declaration; deleting the line returns to the Latin default.
4. `contracts/font_sets.draft_font_metrics(set_ids, base_descriptor)` builds the descriptor: the base descriptor header (`algorithm`, `missingFont`) with the union of the named sets' assets, deduplicated by (family, weight), in declared order.
5. `resolve_draft_render`: an explicit `--font-metrics` wins; else the preset's `fontSets` build the descriptor; else the packaged default. Installed faces remain a fallback behind it (#1281), unchanged.

## Not changed

Render Context schema, closure identity of immutable renders, design YAML, `examples/**`. A preset without `fontSets` renders byte-identically.

## Tests

Schema accepts/refuses; loader copies the declaration; draft render with the declaration renders `第`/`日` under `use_installed_fonts(InstalledFontIndex((), files=()))`, and the same preset without it refuses with `E_FONT_GLYPH_UNAVAILABLE`; explicit `--font-metrics` wins; provider missing gives `E_FONT_METRICS_UNAVAILABLE`; then `titlecard` and `yuya` registered with the declaration (entries from `8ebabcdb1`, name-scoped TikZ refusal for titlecard).
