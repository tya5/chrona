<!-- chrona:literal-acceptance/v1 -->

# Acceptance review — synthetic small-caps `textTransform` (#1285)

Implementation: [#1332](https://github.com/tya5/chrona/pull/1332) (merge `3d363889`), checked against `origin/main` `289444de`. `textTransform: small-caps` sets a role's lowercase letters as capitals at `smallCapsScale` times the role size; the scale is a named number token strictly between 0.5 and 1 with no default. Layout measures each run at its own size and completes `runs`; the Scene carries them (`textLayout.runs`, `chrona/scene/v0.7`; the default stays v0.6); SVG sets each run at its size; Typst and TikZ refuse with `E_VISUAL_CAPABILITY_UNSUPPORTED`. Schema: `theme-v0.15` and `scene-v0.7` additive, two `textTransform` enum widenings as expected-delta lines. Specifications 07 and 08 state the rule; no font and no font metrics are added. Plan: [Status comment](https://github.com/tya5/chrona/issues/1285).

## Literal issue acceptance

### Issue #1285

- Source: [Issue #1285](https://github.com/tya5/chrona/issues/1285) (body, assignment and Status comments)
- Observed: 2026-10-10

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | For a lowercase-bearing string, Scene text runs for former lowercase letters have size equal to the role size times the declared scale and are uppercase; original capitals keep the role size. | met | [`test_small_caps.py`](../../../tests/integration/test_small_caps.py) `test_former_lowercase_letters_are_capitals_at_the_declared_scale_and_original_capitals_keep_the_size`: "Imaging Team" becomes `IMAGING TEAM`, the letters of the former lowercase positions have size `font_size x 0.8`, the two capitals keep `font_size`, and every run text is upper case. `test_the_svg_sets_each_run_at_its_own_size_and_the_scene_validates` shows the runs reach the SVG as `tspan` sizes and the Scene validates as `chrona/scene/v0.7`. | — |
| 2 | Measured inline size equals the sum of run measurements (Scene-checkable); absent transform is byte-identical. | met | `test_the_measured_inline_size_is_the_sum_of_the_run_measurements_plus_the_spacing_between_runs` in the [same file](../../../tests/integration/test_small_caps.py) (bounds inline size equals the sum of the runs' `inline_size` plus the letter spacing between runs; the plus term is the schema-stated rule in [`scene-v0.7.schema.yaml`](../../../schemas/scene-v0.7.schema.yaml) `textLayout.runs`). Absent transform: `test_without_the_transform_there_are_no_runs_and_the_output_is_unchanged` (no runs; equals an explicit `none`, a weak check on its own). The stronger evidence is the [PR count table](https://github.com/tya5/chrona/pull/1332): all 45 slides rendered on the base and on the head were byte-identical in SVG and Scene JSON, and no Theme in the corpus or the presets declares `small-caps` (search on `289444de`). The sum is checked on the in-memory Scene text layout, not by a test over the serialised JSON. | — |
| 3 | Synthetic fixture test. | met | The same [test file](../../../tests/integration/test_small_caps.py) builds its own Project (`_source`, packaged `executive-light` bundle with `groupHeader` bound to `small-caps`) and reads no `examples/**`. It also covers the refusal cases: missing scale `E_THEME_ROLE_REQUIRED`, scale 1.0 and 0.5 `E_THEME_TEXT_SCALE_RANGE`, scale beside another transform `E_THEME_TEXT_TREATMENT_CONFLICT`, and Typst/TikZ `E_VISUAL_CAPABILITY_UNSUPPORTED`. All pass on `289444de`. | — |
| 4 | Do not edit `examples/**`. | met | [Diff](https://github.com/tya5/chrona/pull/1332/files): schemas, the expected-delta file, Specs 07 and 08, `layout/`, `model/`, `scene/`, `renderers/`, `tools/check_scene_primitive_delivery.py` and the test; no `examples/**` and no bot-generated file. | — |
| 5 | The reviewer adopts it in slide 25. | deferred | Reviewer step, not a developer closing condition: the [Sunday Strip Theme](../../../examples/halcyon-1/themes/sunday.yaml) does not yet use `small-caps` (search on `289444de`). Owner note: adoption is the reviewer's YAML change in slide 25 and needs no code here. | [#1269](https://github.com/tya5/chrona/issues/1269): assemble the Sunday Strip target; adoption of small caps in slide 25. |

## Programme-level criteria (optional)

None. Rows 1 to 4 are met; row 5 is the reviewer's adoption step on #1269. The issue can close after this review and the three-OS run on the `main` commit that publishes it are cited, unless the owner wants adoption confirmed first.
