<!-- chrona:literal-acceptance/v1 -->

# Issue #588: hand-wobble stroke treatment and per-state value affixes, acceptance review

Source: [Issue #588](https://github.com/tya5/chrona/issues/588), observed 2026-10-03 (body unchanged since filing; the comments on it are this work's claim, its [owner decisions](https://github.com/tya5/chrona/issues/588#issuecomment-5953176877) and state records). The three rows below are the three literal acceptance bullets of the body. Work record: [issue-588-hand-wobble-and-value-affixes-2026-10-02.md](../planning/active/issue-588-hand-wobble-and-value-affixes-2026-10-02.md) (baseline, design plan, design, architecture review, implementation plan, evidence); living contracts [Specification 63](../../specification/63-portable-visual-capabilities.md) section 8, [07](../../specification/07-style-and-theme.md), [08](../../specification/08-scene-and-rendering.md) and [46](../../specification/46-halcyon-resource-authoring.md).

Slices: design [PR #954](https://github.com/tya5/chrona/pull/954) (`17e656ef`); I588-1 hand wobble [PR #958](https://github.com/tya5/chrona/pull/958) (`ce6b67ef`); I588-2 value affixes [PR #965](https://github.com/tya5/chrona/pull/965) (`1d050b85`).

## Literal issue acceptance

### Issue #588

- Source: [Issue #588](https://github.com/tya5/chrona/issues/588)
- Observed: 2026-10-03

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | A Theme stroke treatment `wobble` with a declared amplitude and seed. It is deterministic, and SVG and PNG are identical. Bounds used for layout are unchanged, and a test proves it. | met | Theme role properties `wobbleAmplitude`, `wobbleSeed` (and `wobbleWavelength`, `wobbleFidelity`) on Rect and Path roles ([`stroke_wobble.py`](../../../src/chrona/presentation/scene/stroke_wobble.py), [`paint.py`](../../../src/chrona/presentation/scene/paint.py)); the wavelength is declared as well, a superset of the row. Deterministic: an integer-only generator and IEEE basic operations, pinned by golden constants and outline digests in [`test_stroke_wobble.py`](../../../tests/unit/chrona/presentation/scene/test_stroke_wobble.py), two renders byte-identical in [`test_stroke_wobble_render.py`](../../../tests/integration/test_stroke_wobble_render.py). SVG and PNG: the PNG adapter is the same SVG through resvg, and the PNG test shows the wobble where the SVG draws it and nothing else moved. **Bounds:** `test_no_bound_id_or_placement_changes_and_only_the_wobble_differs` proves every Scene primitive equals the straight one once the wobble is stripped (bounds, points, commands, slot, order), and slots, rows, canvas and diagnostics are equal; the ink stays within the amplitude of the nominal outline. 35 mutation checks, all killed. Default output unchanged: regenerating every public slide changed only the new slide. Not verified here: a Windows run; the pinned constants make the three-OS run on the review commit the check. | none |
| 2 | A Theme/View value format declares affixes per state (slip, on-time, ahead, missing). Measurement includes the affixes, and synthetic tests cover each state. | met | View `tableColumns[].affixes` for `slip`, `onTime`, `ahead` and `missing`, with the unit-less `signedNumber` format ([`table_presentation.py`](../../../src/chrona/presentation/table_presentation.py), [`resources.py`](../../../src/chrona/presentation/contracts/resources.py), [`v05_content.py`](../../../src/chrona/presentation/review/v05_content.py)). Declared in the View, not the Theme: content strings are fixed before measurement (owner decision A1). Measurement: the cell string is composed once, and `test_a_content_column_is_exactly_as_wide_as_with_the_affixes_typed_into_the_values` proves the column width equals the width with the affix typed into the value; under ellipsis the affix survives (`test_a_narrow_column_ellipsizes_the_value_and_keeps_the_affix`). Each state: `test_each_state_is_drawn_with_its_own_affix_and_an_undeclared_state_is_unchanged`, `test_prefix_and_suffix_on_every_state`, `test_signed_days_keeps_its_unit_and_the_missing_text_is_wrapped_too`, and the state boundaries in [`test_table_affix_state.py`](../../../tests/unit/chrona/presentation/test_table_affix_state.py). Failures are `E_VIEW_COLUMN_AFFIX` or the View schema. 17 mutation checks, all killed. **Coverage:** table columns only; lane member chips, summary metrics and Detail labels keep their own formatting (disclosed). | none |
| 3 | Evidence: the Sunday slide through YAML. | narrowed | Two Controller Z slides, YAML only, no preset, catalogue or corpus datum edited: [`hand-wobble`](https://github.com/tya5/chrona/blob/abbe91a40b46621e448eded6dcfb42b1dd97bb7b/examples/controller-z/generated/hand-wobble.svg) (hand-inked bars and dependencies) and [`value-affixes`](https://github.com/tya5/chrona/blob/abbe91a40b46621e448eded6dcfb42b1dd97bb7b/examples/controller-z/generated/value-affixes.svg) (a Δ column reading `+4!` and `?`, on the wobble Theme, rich SVG profile). Both were rendered through resvg and read in full; the corpus contrast gate reports 0 errors. They show the two treatments of this issue on the Sunday Δ column and hand-inked marks; the Sunday target also needs inked panels with gutters, which is [#889](https://github.com/tya5/chrona/issues/889), and in-plot speech balloons and the starburst label, which the target README states are not covered by #582 to #588. No existing issue covers assembling the whole slide (searched: Sunday, balloon, starburst, panels). | [#889](https://github.com/tya5/chrona/issues/889) panels with gutters |

## Programme-level criteria (optional)

None.

## Architecture and release conclusion

Theme declares the wobble; Scene completes the outline from Layout geometry and resolves the omission ladder; adapters draw the points and decide nothing; View declares affixes, content normalisation composes the cell once, Layout measures and places it. Scene v0.7, Theme v0.11 and v0.13 gained optional properties in place (Specification 56 section 3.2). The S0 gate `python -m tools.schema_equivalence --base-rev origin/main` classifies the Scene and Theme additions as additive; for the View it needs two expected-delta entries (added). Against `origin/main` the gate also reports pre-existing chained #584 entries as "does not apply" (not this work's, untouched); with them removed in a scratch copy it passes. Corpus data, presets, catalogues and #585 and #491 files were not edited.

Disclosures:

- **A wobbled outline extends past the bounds** by at most the effective amplitude (limit 16 px) plus half the stroke; Layout gaps are not widened.
- **A role shared by a bar and a gate wobbles only the bar** (Symbol, Text and Icon, patterned or image-filled Rects and clip hosts are excluded by rule).
- **`signedNumber` is declared in `view-v0.28`,** not the frozen shared vocabulary part (a change there is a new part version).
- **Typst, TikZ and PDF** follow the baseline ladder; their adapters never draw a wobble.
- **Rendered output was read** from resvg PNGs of the two slides; no browser or other renderer was compared, and a cross-OS raster comparison is not claimed.

Exact review-bearing-main three-OS CI and the newest-Python materializer run must pass before closing #588; that run is recorded in the closing comment.
