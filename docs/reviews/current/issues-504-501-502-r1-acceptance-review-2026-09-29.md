<!-- chrona:literal-acceptance/v1 -->

# R1 release review — readable default and lane table (#504, #501, #502)

PR [#533](https://github.com/tya5/chrona/pull/533) merged head `b307765ea18a852ce5ca71df0609bf0a3b164197` as `2920930596f2aaec270994cfd3b0c266ece78ca8`. Its [four-job CI](https://github.com/tya5/chrona/actions/runs/36512035812) and [exact-main CI](https://github.com/tya5/chrona/actions/runs/36513193268) passed. Focused post-merge checks passed (6 tests), as did the 29-slide public materializer check. Generated 02/03/11/12/16 Scene/SVG changes were inspected; 04/07/15 stayed byte-identical. This review accepts only R1, not the entire #504/#501 programme.

## Literal issue acceptance

### Issue #504

- Source: [Issue #504](https://github.com/tya5/chrona/issues/504)
- Observed: 2026-09-29

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | The bundled default and the `chrona init` starter keep an informative table under lanes. Where a lane holds one item, the lane label is that item's name. Otherwise the default View does not use lanes. Either way, no table column is empty on every row. The #498 gate is extended to assert this. | met | [Default/starter Scene and SVG tests](../../../tests/integration/test_readable_defaults.py) assert automatic Task/Plan rows, populated cells, and no empty Owner column. | — |
| 2 | Lane height can grow into available plot height for stagger rows before a name is suppressed, as a declared Layout policy, for example with `rowDistribution: fill` (#434). A name is suppressed only when the lane cannot grow. On 02, the suppression count is reported in the acceptance review, and every suppressed name is attributed to a lane that could not grow. | deferred | [R1–R5 plan](../../planning/active/issue-504-501-readable-default-implementation-plan-2026-09-29.md) assigns growth and attribution to R2; R1 makes no such claim. | [R2 plan](../../planning/active/issue-504-501-readable-default-implementation-plan-2026-09-29.md) |
| 3 | The lane table does not repeat the group header's text on the group's first lane, and it never shows an empty label next to a count. | met | [Public 02/12 tests](../../../tests/integration/test_readable_defaults.py) require each lane label nonblank and distinct from group headers. | — |
| 4 | A mechanical check over committed lane slides: the ratio of shown to packed names is reported in the corpus coverage, so a regression is visible. | deferred | [R1–R5 plan](../../planning/active/issue-504-501-readable-default-implementation-plan-2026-09-29.md) assigns corpus coverage to R5. | [R5 plan](../../planning/active/issue-504-501-readable-default-implementation-plan-2026-09-29.md) |

The issue's follow-up comment requires the attached-point host to keep a visible title; the [attached-milestones test](../../../tests/integration/test_readable_defaults.py) finds `Launch campaign` in the Task cell and SVG.

### Issue #501

- Source: [Issue #501](https://github.com/tya5/chrona/issues/501)
- Observed: 2026-09-29

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | **Gate.** A test renders the bundled default on the `chrona init` starter and on HALCYON-1. It fails on any `W_LAYOUT_*` diagnostic other than data-state ones (`W_LAYOUT_ACTUAL_INCOMPLETE`, `W_LAYOUT_LABEL_SUPPRESSED`), and on any mark whose bounds leave the `timeline` slot. | deferred | [R1 tests](../../../tests/integration/test_readable_defaults.py) cover table, names and guides, not the complete diagnostic/mark gate. | [R5 plan](../../planning/active/issue-504-501-readable-default-implementation-plan-2026-09-29.md) |
| 2 | Closed days render as a faint fill without per-day outlines, or as merged runs, in both the chart and its legend key. | met | [R3 PR #531](https://github.com/tya5/chrona/pull/531) merged before R1; its [exact-main CI](https://github.com/tya5/chrona/actions/runs/36509779338) passed. | — |
| 3 | The as-of label sits outside the axis lanes: in the plot's top margin, or as a chip on the rule. | deferred | [R1–R5 plan](../../planning/active/issue-504-501-readable-default-implementation-plan-2026-09-29.md) assigns this to R4; the starter still reproduces an axis overlap. | [R4 plan](../../planning/active/issue-504-501-readable-default-implementation-plan-2026-09-29.md) |
| 4 | Point marks on the domain's first or last day are fully inside the plot. | deferred | [R1–R5 plan](../../planning/active/issue-504-501-readable-default-implementation-plan-2026-09-29.md) assigns shared scale/endpoint geometry to R4. | [R4 plan](../../planning/active/issue-504-501-readable-default-implementation-plan-2026-09-29.md) |
| 5 | An end-side member label is placed within a bounded distance of its mark (a few em). Past the bound it takes `start`, or is suppressed and counted. A Scene check measures the gap. | deferred | [R1–R5 plan](../../planning/active/issue-504-501-readable-default-implementation-plan-2026-09-29.md) assigns the bound and Scene check to R4. | [R4 plan](../../planning/active/issue-504-501-readable-default-implementation-plan-2026-09-29.md) |
| 6 | Optional: the starter's plot height follows its rows, and a column whose source is missing on every row is omitted or declared. | deferred | [R1 default View](../../../src/chrona/resources/presets/bundles/editorial-readable-default/view.yaml) removes Owner; no row-following canvas contract is approved. | [Canvas-sizing decision in R1–R5 plan](../../planning/active/issue-504-501-readable-default-implementation-plan-2026-09-29.md) |

### Issue #502

- Source: [Issue #502](https://github.com/tya5/chrona/issues/502)
- Observed: 2026-09-29

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | Select a meaningful declared table policy for group-less lane Views (for example `label: lane`, or an explicitly omitted lane table); do not infer a title from an arbitrary member. | met | [View policy](../../../examples/halcyon-1/views/03-launch-campaign.yaml) declares lane identity; the [public test](../../../tests/integration/test_readable_defaults.py) requires populated distinct labels. | — |
| 2 | The public 03 SVG/Scene shows that policy, with unchanged lane/member IDs and relation routes unless separately attributed. | met | [Committed 03 Scene](../../../examples/halcyon-1/generated/03-launch-campaign.scene.json) and [SVG](../../../examples/halcyon-1/generated/03-launch-campaign.svg) show the policy; [PR #533](https://github.com/tya5/chrona/pull/533) confirms preserved IDs/routes. | — |
| 3 | Focused View/resource tests, regenerated public evidence, and affected CI gates pass; unrelated automatic output stays byte-identical. | met | [Focused tests](../../../tests/integration/test_readable_defaults.py), [public materializer](../../../tools/regenerate_public_examples.py), and [PR CI](https://github.com/tya5/chrona/actions/runs/36512035812) passed; [PR #533](https://github.com/tya5/chrona/pull/533) records unchanged 04/07/15 bytes. | — |

## Programme-level criteria (optional)

R1 supplies the default/table and #502 policy; #504 growth and corpus reporting plus #501 as-of/scale/gate work remain in the linked plan. #504 and #501 stay open. #502 may close after this review merges and its exact-main CI passes.

## Architecture conclusion

View owns row/table intent, Layout owns completed placement, Scene projects it, and adapters serialize it. R1 did not change those boundaries. No issue is closed by this review commit itself.
