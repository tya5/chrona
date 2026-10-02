<!-- chrona:literal-acceptance/v1 -->

# Issue #493 — axis secondary label acceptance review

Source: [Issue #493](https://github.com/tya5/chrona/issues/493), observed 2026-10-02 (body unchanged since filing, plus comments of the implementing session only: the claim, the owner decisions with a correction for D6, and status blocks). The issue has one acceptance row, copied below. Design: [work record](../../planning/active/issue-493-axis-secondary-label-2026-10-02.md) (baseline, design plan, design, architecture review, implementation plan), living contract [Specification 39](../../specification/39-axis-and-observation-clarity.md) "Axis secondary labels (#493)".

Slices: design publication [PR #933](https://github.com/tya5/chrona/pull/933) (`b23f9338`); design amendment adding `labelGap` before code [PR #936](https://github.com/tya5/chrona/pull/936) (`f3612a87`); code [PR #941](https://github.com/tya5/chrona/pull/941) (`c5607388`); committed slide [PR #943](https://github.com/tya5/chrona/pull/943) (`0aeabda4`), with the main-sync evidence commit `2665ae1c`. Owner decisions (options, choice, why, reversal) are [comments on the issue](https://github.com/tya5/chrona/issues/493#issuecomment-5949522195) and [its correction](https://github.com/tya5/chrona/issues/493#issuecomment-5951687403), and work record section 5.8.

## Literal issue acceptance

### Issue #493

- Source: [Issue #493](https://github.com/tya5/chrona/issues/493)
- Observed: 2026-10-02

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | A labels tier can declare a secondary form rendered smaller in the same cell, both measured and fitted, and one committed slide shows it. | met | A fixed-unit horizontal labels tier declares `label.secondary {form, nameTable?, typographyRole, placement: stacked or inline}` ([`view-v0.28`](../../../schemas/view-v0.28.schema.yaml), `$defs/axisSecondaryLabel`; `unit: auto`, rotated text, missing members and a form of another unit are rejected). Layout ([`surface_axis.py`](../../../src/chrona/presentation/layout/surface_axis.py) `_secondary_plan`, `_secondary_outcomes`, the `labels` branch) formats it through its own name table, **measures it with the same `measure_text_width` and the font metrics of its own text role** (no width constant; the inline gap is one measured space or a Theme `labelGap`), fits it against the cell's available inline size and the lane block, and draws it smaller in the same cell as `axis-label-secondary:<tier>:<index>`. Not fitting: omitted with `W_LAYOUT_AXIS_SECONDARY_OMITTED:<id>:does-not-fit` or `primary-does-not-fit` and a suppressed placement decision, the primary stays on its tier baseline; a stack the lane or slot cannot hold is `E_PRESENTATION_AXIS_OVERFLOW` (`secondary-lane:<tier>`); the primary's fit and thinning never depend on it. 25 Layout tests in [`test_axis_secondary.py`](../../../tests/unit/chrona/presentation/scene/test_axis_secondary.py) (fixture font, so every geometry is an independent computation: stacked and inline positions, `start` and `center` alignment, each omission reason with its diagnostic, decision and outcome, thinned primary, lane growth and centring, lane overflow, missing Theme role, gap, default path) and 26 declaration and gate tests in [`test_axis_secondary_declaration.py`](../../../tests/integration/test_axis_secondary_declaration.py) (schema accept and reject per unit, name-table inheritance, a rendered Scene through a packaged preset, the perceptibility gate finding no error and reporting `E_SCENE_TEXT_INTERSECTION` when a secondary is forced over its primary). 23 mutants killed. Committed slide: Controller Z (Japanese register) [`axis-secondary`](../../../examples/controller-z-ja/generated/axis-secondary.svg) (manifest [entry](../../../examples/controller-z-ja/manifest.yaml); [view](../../../examples/controller-z-ja/views/axis-secondary.yaml), [Theme](../../../examples/controller-z-ja/themes/axis-secondary.yaml) and [context](../../../examples/controller-z-ja/contexts/axis-secondary.yaml) beside it): five month cells each hold the `ja-JP` month (`2月`, 12 px, baseline 95.2) and beneath it the upper-cased `en-US` month (`FEB`, 9 px, baseline 107.5), measured with Noto Sans JP. Rendered and read: the two lines stack and centre in every cell under the half-year line, no overlap; `tools/check_scene_perceptibility.py` PASS (0 errors over every committed scene, 35 on the review base) and the public axis-label overlap test now covers the secondary texts. | — |

## Programme-level criteria (optional)

None.

## Architecture and release conclusion

The View gained one optional member and the Theme one optional role property, both in place (Specification 56 section 3.2): `python -m tools.schema_equivalence --base-rev origin/main` reported `additive=2` (theme-v0.11, theme-v0.13), `delta=1` (view-v0.28, one expected-delta entry for the tier-label member) and PASS. Layout owns the geometry and the omission and lane rules; Scene, the adapters and the semantic registry are untouched (one more Text primitive per drawn secondary, hosted like its primary, so the existing perceptibility gates cover it). The default path is unchanged: `tools/regenerate_public_examples.py --check` was byte-identical for all 32 slides before the new one, and the slide PR changed no existing slide.

The design changed once before code: reading the rendered inline probe (`Jan` then `01` after one measured space) showed it reads as one token, so D6 gained the optional `labelGap` property in a docs PR (#936) published before the code.

Disclosures:

- **Not delivered, by design and not filed:** a `corner` placement (Tenth Frame's corner sub-box needs a Theme-owned box; additive `placement` value), a secondary colour distinct from its tier's (additive: a registered semantic id and Scene role), `unit: auto` tiers and rotated text (schema branches would widen), and kanji-numeral month names such as `三月` (not a name-table form; a table-data matter under #432). The issue's acceptance row requires none of them. Searched open issues for a duplicate before not filing (`sub-box`, `corner box`, `secondary label colour`): none.
- **Targets.** The Title Card and Tenth Frame mocks were read as pictures and READMEs only; no preset or catalogue Theme was edited, so neither target's preset adopts a secondary label yet (a preset-owner decision, #718 area).
- **CJK rendering.** The slide's measurements use the Noto Sans JP metrics of the optional provider; the PNG used to read it was drawn by Chrome with a system fallback CJK face, so pixel gaps in that picture are the fallback face's, not the measured ones. The committed SVG carries the measured positions.
- **Test-suite counts moved with the new slide** (as of its merge; later slides by others moved them again): 34 slides, 305 axis labels (12 new: 2 half-year, 5 month, 5 secondary), 77 derived paths.

Exact review-bearing-main three-OS CI and newest-Python materializer run must pass before closing #493; record that run in the issue closing comment.
