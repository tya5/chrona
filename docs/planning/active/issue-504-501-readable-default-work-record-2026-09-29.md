# #504/#501 readable-default work record

## Published baseline and design plan

Public `main` is `5408ef2d`; its bundled default selects the Editorial-derived View with lane mode, `[explicit, attached]` packing and `laneTable: {label: group, count: true}`, the Editorial Layout with `rowDistribution: pack`, and the readable-default Theme with outlined `calendar-closed`. The issues' measured defects are reports from earlier main commits, not yet independently reproduced on this base. #498's existing gate checks names/suppression but not table meaning, endpoint containment, or as-of/closed-day appearance. #434 already provides a declared `fill` Layout policy. [#502](https://github.com/tya5/chrona/issues/502) has an overlapping group-less lane-table requirement; its independent public-03 acceptance must not be silently counted complete. #526 precedes release work because main CI is red.

Literal [#504](https://github.com/tya5/chrona/issues/504) acceptance (including its later host-name comment):

1. The bundled default and the `chrona init` starter keep an informative table under lanes. Where a lane holds one item, the lane label is that item's name. Otherwise the default View does not use lanes. Either way, no table column is empty on every row. The #498 gate is extended to assert this. The host of attached points keeps a visible name, in the lane label or in the plot.
2. Lane height can grow into available plot height for stagger rows before a name is suppressed, as a declared Layout policy, for example with `rowDistribution: fill` (#434). A name is suppressed only when the lane cannot grow. On 02, the suppression count is reported in the acceptance review, and every suppressed name is attributed to a lane that could not grow.
3. The lane table does not repeat the group header's text on the group's first lane, and it never shows an empty label next to a count.
4. A mechanical check over committed lane slides: the ratio of shown to packed names is reported in the corpus coverage, so a regression is visible.

Literal [#501](https://github.com/tya5/chrona/issues/501) acceptance:

1. **Gate.** A test renders the bundled default on the `chrona init` starter and on HALCYON-1. It fails on any `W_LAYOUT_*` diagnostic other than data-state ones (`W_LAYOUT_ACTUAL_INCOMPLETE`, `W_LAYOUT_LABEL_SUPPRESSED`), and on any mark whose bounds leave the `timeline` slot.
2. Closed days render as a faint fill without per-day outlines, or as merged runs, in both the chart and its legend key.
3. The as-of label sits outside the axis lanes: in the plot's top margin, or as a chip on the rule.
4. Point marks on the domain's first or last day are fully inside the plot.
5. An end-side member label is placed within a bounded distance of its mark (a few em). Past the bound it takes `start`, or is suppressed and counted. A Scene check measures the gap.
6. Optional: the starter's plot height follows its rows, and a column whose source is missing on every row is omitted or declared.

Design questions: what lane table policy provides a unique singleton title without inventing a representative for multi-member lanes; how to avoid group-header duplication and blank counted rows; how `fill` interacts with minimum row height and bounded label search; whether optional starter polish can be included without coupling it to architecture fixes; where marker label and endpoint bounds should be completed; and how to prove SVG/Scene output instead of Scene-only claims. Whole-architecture review must check Specs 06/07/08/33/38/39, #467 lane membership, #488 row-band labels, #498 default policy, and #434 `fill` before implementation. Intended public evidence: starter, bare HALCYON, 02/03/11/12, attached-milestones, corpus coverage and generated SVG/Scene diffs. Design slices: table/row policy, closed-day paint, as-of/endpoint/label geometry, then corpus and first-run gate. Each slice must be independently reviewable and publishable.
