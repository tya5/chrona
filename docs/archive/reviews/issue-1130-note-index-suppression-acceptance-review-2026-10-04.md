<!-- chrona:literal-acceptance/v1 -->
# Issue #1130 — numbered annotation list acceptance

Authority: [archived design/review/plan](../planning/issue-1130-note-index-suppression-2026-10-04.md), Specifications 33/46, rule (a).
Implementation/evidence: [PR #1143](https://github.com/tya5/chrona/pull/1143).

## Literal issue acceptance

### Issue #1130

- Source: [#1130](https://github.com/tya5/chrona/issues/1130)
- Observed: 2026-10-04

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| --- | --- | --- | --- | --- |
| 1 | With one of four indexes suppressed, the list and the plot agree under the chosen rule. | met | [Four-annotation Scene/SVG fixtures](https://github.com/tya5/chrona/blob/c113f84a3e2b4a7668b8e5a3e6ebec1d67ca0815/tests/integration/test_annotation_list_status.py): stable ordinals, visible status, three surviving indexes; index-only and whole-callout suppression remain distinct | — |
| 2 | The suppression diagnostic is still reported. | met | [Exact diagnostic assertions](https://github.com/tya5/chrona/blob/c113f84a3e2b4a7668b8e5a3e6ebec1d67ca0815/tests/integration/test_annotation_list_status.py); public Scene warnings retained | — |
| 3 | When nothing is suppressed, the output is byte-identical. | met | [Pre-change Scene/SVG SHA-256 controls](https://github.com/tya5/chrona/blob/c113f84a3e2b4a7668b8e5a3e6ebec1d67ca0815/tests/integration/test_annotation_list_status.py) | — |

## Programme-level criteria (optional)

Layout completes status and text geometry; View ordinals and accepted plot
bodies/leaders remain owned as before. Scene/adapters infer no status.
Public `controller-z/annotations` renders missing summary #4 without restoring
its intentionally suppressed callout. Other changed pairs and diagnostics are
disclosed once in the PR. Explicit label overflow can expand the completed
canvas under Spec 33 §13; it is not silent growth or extra slot capacity.
Closed on main commit [c113f84a3e2b4a7668b8e5a3e6ebec1d67ca0815](https://github.com/tya5/chrona/commit/c113f84a3e2b4a7668b8e5a3e6ebec1d67ca0815); exact-SHA [derived-main/ready](https://github.com/tya5/chrona/actions/runs/37205880868) and [three-OS release gate](https://github.com/tya5/chrona/actions/runs/37206002978) passed.
