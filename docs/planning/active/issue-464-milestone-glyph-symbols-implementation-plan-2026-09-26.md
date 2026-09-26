# Implementation Plan — Milestone Glyph Symbols (#464)

**Public design base:** the commit that publishes the [architecture review](../../reviews/current/issue-464-milestone-glyph-symbols-architecture-review-2026-09-26.md). **Authority:** [design](../../design/issue-464-milestone-glyph-symbols-design-2026-09-26.md), Specification 07 §5.2, Specification 08 §5.3, [Issue #464](https://github.com/tya5/chrona/issues/464). State-dependent glyphs and icon-catalogue-backed parts are out of scope; not implemented here.

## Literal acceptance ledger

1. A Theme can bind `milestoneSymbol` (and its actual and baseline counterparts) to a glyph asset instead of a built-in shape, and every milestone renders with it.
2. A glyph with at least two painted parts renders both, with paints from the Theme or from the asset, and the choice is documented.
3. Planned, actual and baseline variants of one glyph can be distinguished without colour alone.
4. One committed slide renders HALCYON-1 `02-programme-board` with a non-built-in gate glyph, and its evidence is reproducible.
5. Dependency arrows still end at the glyph's edge, and the perceptibility gate passes on that slide.

## Coordination

No other open session owns `theme_tokens.py`, `mark_geometry.py`, `contrast_policy.py`, or the HALCYON-1 `02-programme-board` theme file per the brief's boundaries (#466/#467 own annotation/lane files only). Before each push, fetch `origin/main`, check ahead/behind, and stop on any conflict in `scene/v05_builder.py` or `contrast_policy.py`.

## I464-1: Theme schema and token resolution

**Owners/files:**
- `schemas/theme-v0.11.schema.yaml`: `symbol` value schema gains the `glyph` shape (`viewBox`, `parts[].{d, paint, color?}`), as a `oneOf` alongside the unchanged 4-shape object.
- `src/chrona/presentation/model/theme_tokens.py`: `ThemeTokenView.symbol()` returns the full resolved value mapping (not only `shape`) so callers can read `viewBox`/`parts`; add `variant_symbol(variant)` resolving `milestoneSymbol`/`milestoneSymbolActual`/`milestoneSymbolBaseline` with fallback.
- Theme role registry (wherever `E_THEME_ROLE_PROPERTY_UNSUPPORTED` is enforced, per spec 07 §5.2): register `milestoneSymbolActual`, `milestoneSymbolBaseline` as valid `symbol`-typed role properties.
- `icons/normalizer.py`: extract the `_path`/`M L H V Q C Z` tokenizer into a helper importable without pulling in icon-specific viewport/PNG validation, for `mark_geometry.py` to reuse (per the design's "exactly one grammar" commitment).

**Focused tests** (`tests/unit/chrona/presentation/model`, `tests/unit/chrona/presentation/scene`):
- a `glyph` value with `viewBox`/two parts validates and round-trips through `ThemeTokenView.symbol()`;
- a `glyph` value missing `viewBox` or with an empty `parts` fails `E_THEME_SCHEMA`;
- `variant_symbol("actual")` returns `milestoneSymbol`'s value when `milestoneSymbolActual` is unset, and its own value when set;
- an unset `milestoneSymbolBaseline` on an otherwise-unrelated role still raises `E_THEME_ROLE_PROPERTY_UNSUPPORTED` for a genuinely unregistered property name (no over-widening of the registry).

## I464-2: Scene construction — multi-part glyph geometry and paint

**Owners/files:**
- `src/chrona/presentation/scene/mark_geometry.py`: `symbol_geometry` gains the `glyph` branch (contain/centre transform from `viewBox` into `bounds`, reusing the shared path tokenizer from I464-1); returns the per-part transformed geometry the builder needs to plan sibling primitives.
- `src/chrona/presentation/scene/v05_builder.py`: the five point-mark emission sites resolve `variant_symbol(variant)` instead of the bare `symbol()` call; when the resolved value's shape is `glyph`, emit one sibling `Symbol` primitive per surviving part (after `paint: "none"` omission) with shared `sourceRef`/`purpose`/`visualRole`/`bounds`/`slotId`/`href`/`linkTitle`/`endTreatment` and ascending `paintOrder`; when it is a built-in shape, behavior is unchanged (one primitive).
- `_complete_primitive_paint`/`_paint_family`: add the per-part paint composition described in Contract 3 (outline-mode role → every part strokes with the role's colour/dash, ignoring literal part colour; solid-mode role → each part's own `paint`/`color` chooses fill or stroke, literal colour overriding the role's default).
- `scene/model.py`: unchanged (confirms the design's "no Scene model change" claim — if implementation finds this untrue, pause and amend the design per AGENTS.md before continuing).

**Focused tests** (`tests/unit/chrona/presentation/scene`):
- a two-part glyph (one role-filled part, one literal-colour part) resolved for `purpose="planned"` emits two `Symbol` primitives with the expected `fill` values and ascending `paintOrder`;
- the same glyph resolved for a `pattern: outline` role emits two stroke-only primitives in the role's colour, and the literal part colour does not appear anywhere in the output;
- a `paint: "none"` part emits no primitive;
- a built-in shape (`diamond`) still emits exactly one `Symbol` primitive, byte-identical to today (regression guard for the "no change to existing 22 slides" constraint).

## I464-3: contrast ground-stacking fix

**Owners/files:**
- `src/chrona/presentation/scene/contrast_policy.py`: widen `_ground_under`'s prior-primitive kind filter from `{"Rect"}` to `{"Rect", "Symbol"}`.

**Focused tests** (`tests/unit/chrona/presentation/scene/test_contrast_policy.py` or equivalent):
- two same-bounds `Symbol` primitives, the second painted over the first: the second's contrast finding's ground is the first's fill, not the canvas;
- unchanged behavior for a `Symbol` with nothing painted over it (ground stays canvas) — regression guard;
- unchanged behavior for the existing `Rect`-over-`Rect` ground case.

**Public evidence check for this slice specifically:** run `tools/presentation_contrast.py` (write, then re-run to confirm stability) over the corpus *before* I464-4's new theme exists, to confirm the widened filter alone produces byte-identical rows for all 22 current slides — isolates this slice's blast radius from the new glyph's.

## I464-4: SVG adapter and the committed HALCYON-1 slide

**Owners/files:**
- `src/chrona/presentation/renderers/v05_svg.py`: no branch change expected (already loops all primitives and already knows how to draw one `Symbol`); confirm during implementation and record if a change was in fact needed.
- A new theme (or a themed copy of `wallboard.yaml`, per the design's target survey) binding `milestoneSymbol` to a two-part glyph (a simple, small, license-free vector — e.g. a two-part pin or flag shape approximating Tenth Frame's or Sunday Strip's direction, authored directly in this repository, not copied from the `*-target-2026-09-26/` HTML mockups which are hand-drawn references, not assets) for HALCYON-1's `02-programme-board`. Bind `milestoneSymbolBaseline` to the same value (inheriting the outline treatment already on the snapshot role) to exercise the "distinguished without colour alone" criterion.
- `examples/halcyon-1/manifest.yaml`/context: add the new committed slide entry (additive; the existing 22 slides' entries are untouched).

**Focused tests** (`tests/integration`, `tests/cli`):
- rendering the new slide produces the expected count of `Symbol` primitives per gate (parts × milestones) and no `E_*` diagnostics;
- the new slide's dependency arrows terminate within the glyph's bounding box on both axes (regression guard for Contract 6's stated constraint, checked directly rather than assumed).

**Public evidence:**
- `tools.regenerate_public_examples --write --jobs 6` then `--check`: expect **one new slide's** files and **no byte change** to the other 22. Attribute the new slide's diagnostics/warnings explicitly; any change elsewhere is a defect, not an expected side effect.
- Refresh `tools/diagnostic_inventory.py`, `tools/presentation_contrast.py`, `tools/presentation_font_identity.py`, `tools/presentation_coverage.py` (write mode) to add the new slide's rows; diff every other row for byte identity.
- `tools/check_scene_perceptibility.py` / `conformance/run_conformance.py`'s `scene-perceptibility` check passes on the new slide with zero errors (literal bullet 5's second half).
- Render before/after PNG crops of the new slide's gates (resvg_py + PIL) and inspect that both parts are visible and that planned/actual/baseline read apart without colour (grayscale crop comparison).

**Gate:** focused tests (`tests/unit/chrona/presentation`, `tests/integration`, `tests/cli`), `conformance/run_conformance.py`, the four diagnostic/contrast/font-identity/coverage tools (write mode) then conformance again, then the full 22+1-slide batch diff, then push and the CI matrix. The slice review is published separately, CI links left `CI: pending`.

## I464-5: issue acceptance

A separate acceptance review under `docs/reviews/current/`, with one row per literal criterion, direct test links, the new slide's rendered SVG/PNG evidence, the batch materializer diff (confirming exactly one slide added and zero bytes changed elsewhere), the contrast/perceptibility tool output, and the green CI run. Close #464 only then, and only after filing the state-dependent-glyph follow-up issue named in the design plan so it is not lost.

If an implementation step finds `scene/model.py` does need a change (I464-2's regression guard), or that the batch diff shows an unexplained byte change on any of the other 22 slides (I464-3 or I464-4), pause, publish a design correction, and amend this plan before continuing, per AGENTS.md.
