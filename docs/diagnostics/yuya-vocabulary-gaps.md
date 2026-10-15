# Yuya: the reference elements chrona does not express (#429 row 4)

The `yuya` catalogue preset references the packaged design `src/chrona/resources/designs/yuya/` in place with the shared generic View `presets/bundles/design-default/view.yaml`. This report names every difference between the preset's rendered slide and its generated reference, with the capability each would need. Reference: [yuya-target-2026-09-26/02-programme-board.png](../research/presentation/yuya-target-2026-09-26/02-programme-board.png) (1600 x 900 hand-drawn mock; not chrona output). Render: `chrona render --preset yuya examples/halcyon-1/project.yaml --actual examples/halcyon-1/actual.yaml --format png` at `cdf6b4b81`, and `examples/chrona-roadmap/project.yaml` for a second project (status ok). Both images were read directly; measurements are by eye unless a number is cited, and canvas heights are from the PNG header. Row pitch, pixel offsets and colour values are not measured.

Reading rule. The reference is the HALCYON mock (26 work packages in six groups); the draft render is halcyon-1 as the project stands (29 work packages, two `objectType` groups, `point` and `span`). The example slide `22-yuya` reaches more of the reference because its own View names HALCYON's fields, window, periods and annotations. The preset's View is generic by design (#1492) and names no project value, so those rows are bundle-side choices, marked "bundle-side" below; they need no new capability.

| # | Name | Reference shows | Chrona draws | Missing capability | Tracked in |
| --- | --- | --- | --- | --- | --- |
| 1 | `icon-catalogue-carried-by-entry` | lantern gates, seigaiha, scroll and seal artwork | drawn because the library entry pins `chrona-target-parts` and `chrona-annotation-parts`; a copy or another entry that omits them loses the artwork | none: the entry carries it. A user preset must list both catalogues | none |
| 2 | `vertical-group-tags` | six plates `壱 · 機体` ... `陸 · 運用`, ordinal and bilingual title | two tan plates reading `point` and `span` vertically; no ordinal, no kanji | a Project-declared standard grouping field; ordinal tag text not investigated | #429; #883 |
| 3 | `group-header-rows` | light bands with the group name over its rows | none: group rows are untinted (owner choice B, 2026-10-06) | none: deliberate | none |
| 4 | `scroll-notes-absent` | three hanging-scroll notes with 危 / 記 seals | no notes; no `annotationBindings` in the generic View | none: delivered (#848, #1167) | bundle-side |
| 5 | `launch-window-absent` | seigaiha band with `出航の窓 · LAUNCH WINDOW` | no band | none: delivered (#582, #1178) | bundle-side |
| 6 | `baseline-ghost-absent` | dashed baseline outline beside the plan bar on the changed rows | no ghost; the legend still lists `baseline`. `baselineMarks: ghost-when-changed` draws nothing without a Snapshot (by design, #1492); no diagnostic | a draft-render way to supply a baseline Snapshot | #1533 |
| 7 | `kanji-axis-names` | `三月` ... `十一月`, `第一四半期` | `Feb` ... `Dec`, `Q1 2027` (the locale is the render's) | a View vocabulary enum for kanji month and quarter names (class c) | none |
| 8 | `title-plate-text` | `計画表  HALCYON-1`, subtitle `PROGRAMME BOARD · 二〇二七年 · 工学暦`, lantern string | plate with `HALCYON-1` only; no lanterns | none: wording is project and Layout data; lantern string is ornament (class c) | none |
| 9 | `as-of-marker` | indigo line, `今` marker, chip `本日 八月二十日 · AS OF` | indigo dashed line and chip `TODAY 20 Aug` | none: wording (class c) | none |
| 10 | `legend-bilingual` | `基準 baseline`, `計画 plan` ... | English only; extra `non-working day` and `calendar exception` entries | none: legend wording is a Layout choice | bundle-side |
| 11 | `serif-faces` | Mincho / serif faces | Noto Sans JP; the slip suffix `日` is drawn through the declared font set `chrona.noto-sans+jp` | none: chrona packages no Mincho. Fonts: the declared font set adds candidates; a missing provider is skipped with `W_FONT_FAMILY_SKIPPED`, then installed fonts are used (soft font sets, Refs #429). | #429 |
| 12 | `decoration-contrast-warning` | pale stripes on hinoki | `W_SCENE_DECORATION_CONTRAST` (27, lowest 1.05:1) and `W_SCENE_MARK_CONTRAST` (legend swatch 2.59:1 against 3:1) | none identified; a reviewer choice | bundle-side |
| 13 | `canvas-height` | 900 px | 864 px (29 rows against 26) | none | not measured |

Reached as drawn: two grounds (night river and hinoki board, red board frame), lacquer title plate with gold lettering, the one-job palette (plan green, actual lacquer red, gates vermilion, as-of indigo), lantern gates, finish deltas in days (`+3日`), dependencies entering from the side, hatch for in-progress work, quarter tier as a dark band.

Not measured: pixel positions, colour values, ordinal tag text.
