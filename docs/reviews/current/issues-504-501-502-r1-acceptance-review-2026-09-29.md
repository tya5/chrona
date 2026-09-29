<!-- chrona:literal-acceptance/v1 -->
# R1 implementation and release review — #504, #501, #502

**Disposition:** R1 is accepted on published `main`; R2/R3/R4/R5 remain deferred. This slice review does not close any issue. It covers [PR #533](https://github.com/tya5/chrona/pull/533), head `b307765ea18a852ce5ca71df0609bf0a3b164197`, merged as `2920930596f2aaec270994cfd3b0c266ece78ca8` on 2026-09-29. Review baseline is that merge commit.

The published [implementation plan](../../planning/active/issue-504-501-readable-default-implementation-plan-2026-09-29.md) defines R1 as default/table semantics, R2 as lane growth, R3 as closed-day paint, R4 as mark/label geometry, and R5 as release gates/corpus evidence. The #504 follow-up comment also requires the attached-milestones host task name to remain visible. The architecture review assigns table identity and label intent to View, completed geometry to Layout, and Scene/adapter their projection/serialization roles.

## Evidence

- The bundled default and `chrona init` starter now render automatic `Task`/`Plan` rows; all 26 HALCYON task/date cells and all 3 starter cells are populated, and the universally empty Owner column is absent. The #498 regression gate checks table content, row guides, Scene and SVG output. Tests also render the `attached-milestones` example and require `Launch campaign` in the Task cell and SVG.
- Counted lane Views use stable nonblank lane identities. The committed public 03 Scene/SVG checks require distinct visible `Lane …` labels. Public 02/12 checks require nonblank labels distinct from group headers and assert the `bustest-integration` route identity remains present in Scene and SVG. The plan and PR report public 03 lane/member IDs and route points unchanged, and 04/07/15 Scene/SVG bytes unchanged.
- Focused post-merge checks reported by PR #533: 6 passed; public materializer checks: 29 passed. [PR CI run 36512035812](https://github.com/tya5/chrona/actions/runs/36512035812) passed all four jobs (Ubuntu, macOS, Windows conformance/full pytest/wheel, plus newest-Python materializer reproduction). [Exact-main CI run 36513193268](https://github.com/tya5/chrona/actions/runs/36513193268) also passed all four jobs. This review independently inspected the committed test assertions and generated public Scene/SVG files; it did not rerun the test suite.

## Literal issue acceptance

### #504

| # | Literal acceptance criterion | Disposition | Evidence / successor |
|---|---|---|---|
| 1 | The bundled default and the `chrona init` starter keep an informative table under lanes. Where a lane holds one item, the lane label is that item's name. Otherwise the default View does not use lanes. Either way, no table column is empty on every row. The #498 gate is extended to assert this. | met for R1 | Default and starter checks establish informative Task/Plan columns and populated cells; the bundled default is automatic-row mode, and the regression test inspects Scene and SVG. See `test_bundled_default_uses_task_and_planned_date_columns` and `test_init_starter_default_uses_task_and_planned_date_columns`. |
| 2 | Lane height can grow into available plot height for stagger rows before a name is suppressed, as a declared Layout policy, for example with `rowDistribution: fill` (#434). A name is suppressed only when the lane cannot grow. On 02, the suppression count is reported in the acceptance review, and every suppressed name is attributed to a lane that could not grow. | deferred | R2 owns lane growth and suppression attribution. This review makes no R2 acceptance claim. |
| 3 | The lane table does not repeat the group header's text on the group's first lane, and it never shows an empty label next to a count. | met for R1 | Public 02/12 tests require every lane label nonblank and unequal to all group headers; public 03 checks nonblank distinct lane identities. |
| 4 | A mechanical check over committed lane slides: the ratio of shown to packed names is reported in the corpus coverage, so a regression is visible. | deferred | R5 owns corpus coverage and shown/packed reporting. |

The issue's follow-up comment says: “The host of attached points keeps a visible name, in the lane label or in the plot.” **met for R1**: the attached-milestones render test requires `Launch campaign` in both its Task cell and serialized SVG text.

### #501

| # | Literal acceptance criterion | Disposition | Evidence / successor |
|---|---|---|---|
| 1 | **Gate.** A test renders the bundled default on the `chrona init` starter and on HALCYON-1. It fails on any `W_LAYOUT_*` diagnostic other than data-state ones (`W_LAYOUT_ACTUAL_INCOMPLETE`, `W_LAYOUT_LABEL_SUPPRESSED`), and on any mark whose bounds leave the `timeline` slot. | deferred | R5 owns this broader release gate; R1's regression gate covers default table/plot names and guides, not the full diagnostic and slot-bound contract. |
| 2 | Closed days render as a faint fill without per-day outlines, or as merged runs, in both the chart and its legend key. | deferred | R3 owns Theme/legend paint and raster/public artifact review. |
| 3 | The as-of label sits outside the axis lanes: in the plot's top margin, or as a chip on the rule. | deferred | R4 owns mark/label geometry. |
| 4 | Point marks on the domain's first or last day are fully inside the plot. | deferred | R4 owns shared scale and endpoint mark geometry. |
| 5 | An end-side member label is placed within a bounded distance of its mark (a few em). Past the bound it takes `start`, or is suppressed and counted. A Scene check measures the gap. | deferred | R4 owns bounded label placement; R5 owns broader regression/evidence gates. |
| 6 | Optional: the starter's plot height follows its rows, and a column whose source is missing on every row is omitted or declared. | deferred | No canvas-sizing contract was approved in R1. The Owner column is now removed from the static default View, but plot-height behavior remains outside this slice; keep #501 open pending an explicit disposition. |

### #502

| # | Literal acceptance criterion | Disposition | Evidence / successor |
|---|---|---|---|
| 1 | Select a meaningful declared table policy for group-less lane Views (for example `label: lane`, or an explicitly omitted lane table); do not infer a title from an arbitrary member. | met | Counted lane Views select stable `lane` identity; public 03 test checks labels are populated, distinct, and prefixed `Lane `. |
| 2 | The public 03 SVG/Scene shows that policy, with unchanged lane/member IDs and relation routes unless separately attributed. | met | Committed 03 Scene/SVG are regenerated with visible lane labels. The public test checks labels in both artifacts; PR #533 reports IDs and route points unchanged. |
| 3 | Focused View/resource tests, regenerated public evidence, and affected CI gates pass; unrelated automatic output stays byte-identical. | met | Focused post-merge tests 6 passed; all 29 public materializers passed; the two cited four-job CI runs are green. PR #533 records unchanged 04/07/15 Scene/SVG bytes. |

## Review result

R1 resolves the blank default table and group-less counted lane labels, and preserves the attached milestone host name and the checked route. No finding in this slice establishes lane growth/suppression attribution, closed-day paint, endpoint/as-of/member-label geometry, corpus ratios, or the complete #501 first-run gate. Keep #504 and #501 open for their successor slices. #502's literal rows are met; close it after this review is published and its exact-main CI passes.
