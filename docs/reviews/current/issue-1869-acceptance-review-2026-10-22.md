<!-- chrona:literal-acceptance/v1 -->

# Literal acceptance review: #1869 rows 1 to 4

Observed on `main` at `a9f41c4b0` (the derived-sync bot commit after [PR #1886](https://github.com/tya5/chrona/pull/1886), `086f4851d`). [Issue #1869](https://github.com/tya5/chrona/issues/1869) has four numbered rows, each with one `Acceptance:` line. The body and its six comments (the lane change to dev B, the status table, the row 3 and row 4 design notes, the reviewer's decisions on rows 3 and 4, and the four-PR status) were re-fetched with `gh issue view 1869 -R tya5/chrona --json body,comments` on 2026-10-22 and counted literally: four rows, no row added since the first reading. Landed: row 1 in [PR #1882](https://github.com/tya5/chrona/pull/1882) (`60c2f69a4`); row 2 in [PR #1884](https://github.com/tya5/chrona/pull/1884) (`aff369334`); row 3 in [PR #1885](https://github.com/tya5/chrona/pull/1885) (`1f99191b0`); row 4 in [PR #1886](https://github.com/tya5/chrona/pull/1886) (`086f4851d`). The issue stays open: row 3 is narrowed to the reviewer's design YAML.

## Method

Private venv `/private/tmp/claude-501/venv1682`, `PYTHONPATH=<worktree>/src:<worktree>`, worktree on `origin/main` `a9f41c4b0`, no shared install. The log starts with the command it records. Focused tests: [pytest-1869.txt](assets-1869/pytest-1869.txt) (71 passed, none skipped, so the resvg route test ran; the full suite was not run). `tests/integration/test_materialize_example.py` is not in the set: its local `E_MATERIALIZER_MISMATCH` is a known local artefact that the PR snapshot pipeline covers. The designs were inspected at this main for the reviewer-owned declarations that row 3 depends on.

## Literal issue acceptance

### Issue #1869

- Source: [Issue #1869](https://github.com/tya5/chrona/issues/1869)
- Observed: 2026-10-22

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | an annotation box never covers a mark of a different object; when no free placement exists, a warning names the covered object. The overflow message reports the space actually available to the failed candidate. | met | Terminal `nearest-free` placement picks a position that covers no other object's mark; otherwise the one covering the fewest, and `W_LAYOUT_ANNOTATION_COVERS_MARK:<annotation-id>:<object-id>` names each covered object ([`test_annotation_covers_marks.py`](../../../tests/integration/test_annotation_covers_marks.py): a free placement covers nothing, the terminal fallback names every covered object and reports the space it had; [`test_annotation_search.py`](../../../tests/unit/chrona/presentation/layout/test_annotation_search.py), [`test_synthetic_surface_rules.py`](../../../tests/integration/test_synthetic_surface_rules.py) for the dense synthetic case; [Spec 33](../../specification/33-intent-oriented-layout.md) section 8.1). `W_LAYOUT_LABEL_OVERFLOW` now reports the box size against the free rectangle the failed candidate had, not the whole surface ([log](assets-1869/pytest-1869.txt)). | — |
| 2 | rasterising the SVG by the documented route keeps every text inside its Scene bounds (synthetic small-caps header test with the resvg route). | met | The SVG adapter fits each completed small-caps run with its own `textLength` instead of one on the whole line ([`v05_svg.py`](../../../src/chrona/presentation/renderers/v05_svg.py)). The synthetic test builds the trial-15 "Δ VS PLAN" heading, rasterises the SVG with `resvg_py` as the README does, and checks the text stays inside its Scene bounds; a second test checks each run is fitted to its own measured size and the whole line is not, a third that the unfitted public SVG is unchanged ([`test_svg_small_caps_resvg_route.py`](../../../tests/unit/chrona/presentation/renderers/test_svg_small_caps_resvg_route.py), all passed and none skipped, [log](assets-1869/pytest-1869.txt)). | — |
| 3 | a column or panel the design declares keeps its width whether or not the data fills it, unless the design declares that it collapses when empty. (Design note: which existing declaration expresses "collapse when empty".) | narrowed | The design note answers the parenthesis on the issue: for a panel, a Layout slot with `priority: optional` is the existing collapse declaration (`preferred` and `required` keep the allocation); for a column there was none, so PR #1885 added the optional `tableColumns[].priority` ([Spec 24](../../specification/24-table-timeline-presentation.md), `view-v0.28` additive member, expected-delta entry), with `optional` (and absent) keeping today's drop, per the reviewer's decision. [`test_table_column_priority.py`](../../../tests/integration/test_table_column_priority.py) pins it: default still drops an unbound comparison column; `preferred` and `required` keep its header and width and the plot-slot inline size and bar width are equal with and without actuals ([log](assets-1869/pytest-1869.txt)). The mechanism is complete; the criterion is not yet true for the five approved designs, because the declarations are the reviewer's YAML: every notes slot (`annotations`) in [`target-b`](../../../src/chrona/resources/designs/target-b/layout.yaml), `titlecard` and `marquee` still reads `priority: optional`, and no design's `finishDelta` column declares `priority` (so the delta column still drops without actuals). Adopting `priority: preferred` there is deferred to reviewer [#1848](https://github.com/tya5/chrona/issues/1848) / owner comparison, as the reviewer stated on the issue; this review does not edit it. | [#1848](https://github.com/tya5/chrona/issues/1848) |
| 4 | Spec states one rule for what the progress fill measures, synthetic tests pin it, and a finished actual remains recognisable by its legend key. | met | [Spec 61](../../specification/61-progress-fill-marks.md) section 1 states the rule: the `planned` source measures its host; the `actual` source measures progress as a fraction of the planned span, drawn from the observed start and clipped to the Actual mark; an Actual with a `finish` draws none; a point, unmatched or extent-less Actual falls back to the host. [`test_progress_fill_planned_span.py`](../../../tests/integration/test_progress_fill_planned_span.py) pins it for rows and lanes (an open Actual's fill is progress times the planned span, clipped; a finished Actual draws no fill, keeps its Actual paint and matches the Actual key, with no Progress key when only finished Actuals exist; the fallbacks), with the existing fill, variance, legend-key and in-progress tests moved to open Actuals ([log](assets-1869/pytest-1869.txt)). The reviewer approved reading A on the issue; the 34 public slides it changes were regenerated in the derived-sync commit `a9f41c4b0`. | — |

Counts: 4 rows, 3 `met`, 1 `narrowed`, 0 `not met`.

## Programme-level criteria (optional)

### Public side effects

This review adds a document and one log under [assets-1869](assets-1869/pytest-1869.txt); it changes no code, schema, specification, guide, preset or example.

| Item | Slides changed | New diagnostics | Schema delta |
| --- | ---: | ---: | --- |
| This review | 0 | 0 | none |

The public effect of the reviewed PRs is in their own bodies: PR #1884 changed 2 of 50 public SVGs (text fit attributes only), PR #1885 changed 0 slides (schema additive), PR #1886 changed 34 of 50 slides (234 to 27 fills drawn, 0 new diagnostics).
