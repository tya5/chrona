<!-- chrona:literal-acceptance/v1 -->
# Issue #1130 — numbered annotation list acceptance

Authority: [current design/review/plan](../../planning/active/issue-1130-note-index-suppression-2026-10-04.md), Specifications 33/46, rule (a).
Implementation/evidence: [PR #1143](https://github.com/tya5/chrona/pull/1143).

## Literal issue acceptance

### Issue #1130

- Source: [#1130](https://github.com/tya5/chrona/issues/1130)
- Observed: 2026-10-04

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| --- | --- | --- | --- | --- |
| 1 | With one of four indexes suppressed, the list and the plot agree under the chosen rule. | met | [Four-annotation Scene/SVG fixtures](../../../tests/integration/test_annotation_list_status.py): stable ordinals, visible status, three surviving indexes; index-only and whole-callout suppression remain distinct | — |
| 2 | The suppression diagnostic is still reported. | met | [Exact diagnostic assertions](../../../tests/integration/test_annotation_list_status.py); public Scene warnings retained | — |
| 3 | When nothing is suppressed, the output is byte-identical. | met | [Pre-change Scene/SVG SHA-256 controls](../../../tests/integration/test_annotation_list_status.py) | — |

## Programme-level criteria (optional)

Layout completes status and text geometry; View ordinals and accepted plot
bodies/leaders remain owned as before. Scene/adapters infer no status.
Public `controller-z/annotations` renders missing summary #4 without restoring
its intentionally suppressed callout. Other changed pairs and diagnostics are
disclosed once in the PR. Explicit label overflow can expand the completed
canvas under Spec 33 §13; it is not silent growth or extra slot capacity.
Release gate: require green final-head PR and exact published review-containing
three-OS/reproduction checks; cite commit and run links in the closing comment.
