<!-- chrona:literal-acceptance/v1 -->

# Issue #911: filled period band in the packaged presets, acceptance review

Source: [Issue #911](https://github.com/tya5/chrona/issues/911), re-fetched 2026-10-03 after the merge (body unchanged since filing, the two comments are this work decision and status block, no new rows). The rows are the literal asks of the body's acceptance proposal and the assignment constraints. Work record: [issue-911-period-band-fill-2026-10-03.md](../planning/active/issue-911-period-band-fill-2026-10-03.md); living contract [Specification 50](../../specification/50-constraint-driven-gantt-surface-quality.md) (period band paragraph).

Slice: [PR #1040](https://github.com/tya5/chrona/pull/1040) (`cf4d2460`), CI green before merge (conformance, three pytest shards, newest-Python reproduction, derived-preview, derived-ready).

## Literal issue acceptance

### Issue #911

- Source: [Issue #911](https://github.com/tya5/chrona/issues/911)
- Observed: 2026-10-03

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | Each packaged Theme paints the band with a fill that passes the contrast gate with marks on it. | met | The eight `theme.yaml` files under [`presets/bundles`](../../../src/chrona/resources/presets/bundles) set `period-band` to `backgroundTreatment: fill` with `period-band.fill` bound to `accent` (`text` in the two print Themes) at opacity 0.12 to 0.16. [`test_period_presets.py`](../../../tests/integration/test_period_presets.py) `test_what_lies_on_the_band_is_judged_on_the_tinted_ground_and_passes` and `test_the_band_is_a_perceptible_highlight_and_the_label_is_legible` run for all eight: no error finding, the band 1.10 or above, the label 4.5 or above, marks judged on a `period-band` ground. Corpus contrast report: 0 errors; perceptibility PASS (53 scenes). | none |
| 2 | No scheme category is required. | met | [`test_period_presets.py`](../../../tests/integration/test_period_presets.py) `test_the_period_roles_bind_only_the_intents_every_color_scheme_has` (every `period-*` binding is one of the nine intents); no scheme, schema or core file changed. | none |
| 3 | A synthetic test renders a period under every packaged Theme, with a preset x scheme sweep. | met | [`test_period_presets.py`](../../../tests/integration/test_period_presets.py) `test_a_view_that_selects_a_period_renders_under_every_packaged_theme` (8 Themes) and `test_a_filled_band_survives_every_packaged_scheme_override` (56 pairs, synthetic Project, no corpus input). 18 of the 56 pairs are refused by the scheme's own gates for the plain View too; the sweep asserts the period adds no refusal and the other 38 render the band in the new scheme's colour. | none |
| 4 | (Assignment) The band reads as a light highlight, not a hole, in HALCYON 02 and at least two presets; images read before and after. | met | Images read before and after ([`test_period_presets.py`](../../../tests/integration/test_period_presets.py) for the assertions): HALCYON 02 (wallboard), `executive-light`, `control-room-dark`, `print-mono`, `technical-print`, `editorial`. The outline bracket became a tint lighter than the plot; the label chip and marks stay legible. `test_the_band_is_a_tint_of_an_intent_that_is_not_the_canvas`. | none |
| 5 | (Assignment) Blocking gates pass: labels on the band at or above the floor (#980, #1013) and the perceptibility gate. | met | [Contrast report](../../diagnostics/presentation-contrast.md) (bot-regenerated after the merge): `period-label` minimum 4.636 against 4.5 and `note-index` minimum 4.597 against 4.5 in the corpus report (the wallboard tint was lowered from 0.22 to 0.16 after `note-index` fell to 4.07); perceptibility 0 errors. | none |
| 6 | (Assignment) The reviewer's `examples/halcyon-1/*target-b*` YAML, core files and other agents' files are untouched. | met | `git diff --stat origin/main` of [PR #1040](https://github.com/tya5/chrona/pull/1040) lists only the eight preset Themes, five HALCYON example Themes, the `12-glyph-gates` identity pins (derived from `wallboard`), Specification 50, the work record and the test. | none |

## Programme-level criteria (optional)

None.

## Architecture and release conclusion

Preset and example YAML only: no schema, Layout, Scene, scheme or adapter change; Specification 50 states the packaged form. Disclosures:

- **Dark opacity 0.16** (decision A of the work record): reverse by restoring the outline form (`backgroundTreatment: outline`, `strokeWidth`, `period-band.stroke`).
- **One new decoration warning** in the corpus report (79 to 80): `annotation-note-box:window-note` on `11-overlay-briefing`, where the box stroke now lies over the band and only its fill (1.056) is judged. Non-blocking (#995) and in annotation artwork (#848's area), so no successor from here.
- **Pre-existing Theme/scheme incompatibilities** (18 of 56 pairs, scale mapping and label contrast) exist without any period; they are not this issue's.

Exact review-bearing-main three-OS CI must pass before closing #911; that run is recorded in the closing comment.
