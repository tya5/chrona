<!-- chrona:literal-acceptance/v1 -->

# Acceptance review — group-header identity targets on corpus slides (#883)

Checked against `origin/main` `ff749b0b`, rendering every corpus slide fresh (`materialize`, no write) and converting the SVG to PNG with the packaged Noto Sans and the Noto Sans JP closure (`resvg`, system fonts skipped). The general knobs are [#583](https://github.com/tya5/chrona/issues/583)'s `grouping.header` (template, ordinal forms) and `grouping.tint`; this issue carries the visual proof on corpus slides. No file was edited: the Views already exist under `examples/halcyon-1/views/`.

## Literal issue acceptance

### Issue #883

- Source: [Issue #883](https://github.com/tya5/chrona/issues/883) (body and the #583 post-review comment)
- Observed: 2026-10-11

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | Target YAML on corpus slides: Marquee `ACT n ·`, Target B per-group tints, Title Card tab; add Views and Themes only, do not edit corpus data. | met | [`24-marquee.yaml`](../../../examples/halcyon-1/views/24-marquee.yaml) declares the header template `ACT {ordinal} · {title}` with `ordinal: roman`; [`21-target-b.yaml`](../../../examples/halcyon-1/views/21-target-b.yaml) declares `grouping.tint` (scale `owner`, domain `firstAppearance`); [`23-titlecard.yaml`](../../../examples/halcyon-1/views/23-titlecard.yaml) declares the template `{ordinal}  {title}` with `ordinal: zero-padded` and the tab decoration; [`22-yuya.yaml`](../../../examples/halcyon-1/views/22-yuya.yaml) declares `ordinal: kanji-formal`. All four are Views and Themes; `project.yaml` and `actual.yaml` are untouched by the slices. | — |
| 2 | Render the reproduced headers on corpus slides and view them as PNG; check readability against the tinted or patterned band (needs #884's contrast class). | met | Rendered and viewed as PNG: Marquee reads `ACT I · SPACECRAFT BUS` to `ACT VI · MISSION OPERATIONS` in gold on the dark maroon band (the `group-header` text is 7.63:1 at its lowest of 12 findings, all `info`); Target B reads dark text on six pale tints; Title Card reads `01 SPACECRAFT BUS` to `06 MISSION OPERATIONS` with the hatched orange tab at each header. The contrast gate reports no `error` for `group-header`, `group-header-band` or `group-tab` on any of the four slides; the lowest ratios are the decorative bands themselves (Target B band 1.13:1, Title Card band 1.12:1, tab 1.12:1 to 2.0:1 on Yuya), all `info`, which is the decoration class (#884). Slides: [Marquee](../../../examples/halcyon-1/generated/24-marquee.svg), [Target B](../../../examples/halcyon-1/generated/21-target-b.svg), [Title Card](../../../examples/halcyon-1/generated/23-titlecard.svg), [Yuya](../../../examples/halcyon-1/generated/22-yuya.svg). | — |
| 3 | Check that each group's tint is distinct. | met | Target B's six group-header bands carry six different fills in the Scene: `#E8EFFA`, `#E4F4EE`, `#FBF0E1`, `#F1E9F8`, `#FDEBEA`, `#D2E9F2` (bus, payload, assembly, ground, launch, operations); in the PNG each band is plainly a different hue. Marquee and Title Card use one band colour by design (`#3A1115`, `#171513`) and distinguish groups by the template. Source: [Target B View](../../../examples/halcyon-1/views/21-target-b.yaml). | — |
| 4 | Check that kanji ordinals (壱 to 陸) are actually drawn with correct glyphs. | met | Yuya's tabs show 壱, 弐, 参, 肆, 伍, 陸 in order, correctly formed, with the Japanese slide title `計画表` and the `2027年` axis; Title Card's CJK heading (`第弐面`, `計画表、`, `発射まで`) also renders with the right glyphs. Source: [Yuya View](../../../examples/halcyon-1/views/22-yuya.yaml). | — |
| 5 | Check that CJK secondary titles are actually drawn with correct glyphs. | deferred | No corpus slide declares a group-header secondary title (the only `secondary:` in these Views is an axis label, see [Title Card View](../../../examples/halcyon-1/views/23-titlecard.yaml)), so there is nothing to draw; the knob is proven on synthetic fixtures only. Adding one is a reviewer-owned `examples/**` change. | [#1375](https://github.com/tya5/chrona/issues/1375): corpus proof for a CJK group-header secondary title. |

## Programme-level criteria (optional)

None. Rows 1 to 4 are met; row 5 moves to #1375 and needs a reviewer change under `examples/**`. The issue can close after this review and #1375 are cited, unless the owner wants the secondary-title proof first.

## How to reproduce

Call `tools.materialize_example.materialize` for each slide of `examples/halcyon-1/manifest.yaml` with `write=False` (a mismatch against committed evidence is irrelevant here: only `review.svg` and `review.scene.json` are read), then `resvg_py.svg_to_bytes` with `dpi=96`, the three packaged Noto Sans faces and the two Noto Sans JP faces of `packages/chrona-fonts-noto-cjk` as `font_files`, and `skip_system_fonts=True`. Contrast findings come from `chrona.presentation.scene.contrast_policy.evaluate_scene_contrast` on the Scene, filtered to the `group-header`, `group-header-band` and `group-tab` roles.
