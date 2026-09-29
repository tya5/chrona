<!-- chrona:literal-acceptance/v1 -->

# Acceptance review — readable first run (#501)

**R1:** [PR #533](https://github.com/tya5/chrona/pull/533), merged as `2920930596f2aaec270994cfd3b0c266ece78ca8`; [CI](https://github.com/tya5/chrona/actions/runs/36512035812) passed. **R3:** [PR #531](https://github.com/tya5/chrona/pull/531), merged as `ef6662e92b5b8ff612f828b1018b5118474cf228`; [CI](https://github.com/tya5/chrona/actions/runs/36508162428) passed. **R4:** [PR #540](https://github.com/tya5/chrona/pull/540), merged as `4e02a9aa3651f47f6221507b83984714dc067653`; its [PR matrix](https://github.com/tya5/chrona/actions/runs/36520151714) and [exact-main matrix](https://github.com/tya5/chrona/actions/runs/36521273399) passed all four jobs.

## Literal issue acceptance

### Issue #501

- Source: [Issue #501](https://github.com/tya5/chrona/issues/501)
- Observed: 2026-09-29

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | **Gate.** A test renders the bundled default on the `chrona init` starter and on HALCYON-1. It fails on any `W_LAYOUT_*` diagnostic other than data-state ones (`W_LAYOUT_ACTUAL_INCOMPLETE`, `W_LAYOUT_LABEL_SUPPRESSED`), and on any mark whose bounds leave the `timeline` slot. | met | [First-run integration gate](../../../tests/integration/test_readable_defaults.py) checks both starter and HALCYON renders, diagnostics, and timeline bounds; the current starter SVG was also rendered and visually inspected. | — |
| 2 | Closed days render as a faint fill without per-day outlines, or as merged runs, in both the chart and its legend key. | met | [R3 PR #531](https://github.com/tya5/chrona/pull/531) and its passing [four-job CI](https://github.com/tya5/chrona/actions/runs/36508162428); public [starter Scene](../../../docs/research/presentation/issue-498-bundled-default-readability-evidence-2026-09-27/starter/default.scene.json) and [SVG](../../../docs/research/presentation/issue-498-bundled-default-readability-evidence-2026-09-27/starter/default.svg). | — |
| 3 | The as-of label sits outside the axis lanes: in the plot's top margin, or as a chip on the rule. | met | [R4 PR #540](https://github.com/tya5/chrona/pull/540), [as-of integration assertions](../../../tests/integration/test_readable_defaults.py), and visual inspection of the current starter render and [HALCYON 04 SVG](../../../examples/halcyon-1/generated/04-tvac-slip.svg). | — |
| 4 | Point marks on the domain's first or last day are fully inside the plot. | met | [R4 PR #540](https://github.com/tya5/chrona/pull/540), [mark-aware scale tests](../../../tests/unit/chrona/presentation/layout/test_mark_aware_scale.py), and the first-run timeline-bound gate in [integration tests](../../../tests/integration/test_readable_defaults.py). | — |
| 5 | An end-side member label is placed within a bounded distance of its mark (a few em). Past the bound it takes `start`, or is suppressed and counted. A Scene check measures the gap. | met | [R4 PR #540](https://github.com/tya5/chrona/pull/540), [bounded-label integration checks](../../../tests/integration/test_readable_defaults.py), and [public HALCYON 02 Scene](../../../examples/halcyon-1/generated/02-programme-board.scene.json). The 29-slide public materializer check passed; starter and 04 SVGs were visually inspected. | — |
| 6 | Optional: the starter's plot height follows its rows, and a column whose source is missing on every row is omitted or declared. | narrowed | R1 removes the universally empty Owner column in the [default View](../../../src/chrona/resources/presets/bundles/editorial-readable-default/view.yaml). The [owner comment](https://github.com/tya5/chrona/issues/501#issuecomment-5882873396) moves row-following canvas sizing to [#538](https://github.com/tya5/chrona/issues/538). | [Issue #538](https://github.com/tya5/chrona/issues/538) |

## Programme-level criteria (optional)

The 29-slide public materializer check passed, and the actual starter and HALCYON 04 SVGs were visually inspected. R4's exact-main four-job CI passed. Close #501 after this review's publication and CI, citing the optional height follow-up #538.

## Architecture conclusion

View owns table intent, Layout owns completed geometry and label placement, Scene carries those results, and adapters serialize them. R1, R3, and R4 are merged and their release evidence passes. The optional height item is explicitly narrowed to #538.
