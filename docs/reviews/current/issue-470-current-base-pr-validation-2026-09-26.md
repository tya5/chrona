# Current-Base PR Validation — Five Presets (#470)

**Issue:** [#470](https://github.com/tya5/chrona/issues/470). **Published integration base:** `ade51cb0d221e2e11ea74b91eeeffb7079707ed2`, after #466 C1. **PR heads tested separately:** #471 `19b8e923`, #472 `3fe4f2a6`, #473 `2ac973b0`, #474 `c2e74795`, #475 `3ce2f9ba`. This is a pre-merge review finding, not an acceptance review and not permission to narrow the issue's literal criterion. No PR has been merged by this review.

Each head merged without conflict into a fresh detached temporary worktree at the published integration base. For #471, the packaged-resource test passed (`6 passed`). A copied `mission-light` preset rendered the HALCYON Project with `examples/halcyon-1/actual.yaml` at requested `--viewport 1600x900`; the copied preset also rendered a fresh `chrona init` starter, retaining its characterized as-of label warning. The same copied-preset HALCYON command was run for #472–#475 in separate uncommitted trial merges. No trial merged to GitHub `main`; the temporary worktree was removed after the review.

| PR / preset | HALCYON Scene diagnostics at requested 1600 × 900 | Actual SVG dimensions |
| --- | --- | --- |
| #471 `mission-light` | `W_LAYOUT_ACTUAL_INCOMPLETE:tvac`; `W_LAYOUT_LABEL_SUPPRESSED:member-label:structure:structure`; `W_LAYOUT_LABEL_SUPPRESSED:variance:detector:detector` | 1600 × 1152 |
| #472 `control-room-dark` | Same three diagnostics as #471 | 1600 × 1152 |
| #473 `print-mono` | `W_LAYOUT_ACTUAL_INCOMPLETE:tvac`; `W_LAYOUT_LABEL_SUPPRESSED:variance:detector:detector` | 1600 × 1111 |
| #474 `executive-light` | `W_LAYOUT_ACTUAL_INCOMPLETE:tvac`; `W_LAYOUT_LABEL_SUPPRESSED:member-label:structure:structure` | 1600 × 1376 |
| #475 `elevated-light` | Same two diagnostics as #474 | 1600 × 1376 |

No `W_SCENE_TEXT_INTERSECTION` was found. The diagnostic strings were read from each emitted Scene, not inferred from CLI stdout. The CLI did not print these warnings for HALCYON, which explains how a CLI-only check could report zero while the persisted Scene reports otherwise. `W_LAYOUT_ACTUAL_INCOMPLETE` is generated for the incomplete TVAC Actual observation by current Layout and exists in the old PR-head code; suppressing it only to satisfy a preset acceptance row would hide a data fact. `W_LAYOUT_LABEL_SUPPRESSED` reflects explicit View suppression after its finite plot-label candidate ladder; #466's shared obstacle closure may change which label fits. Both are `W_LAYOUT_*`, so the literal #470 row 2 is not met if it applies to Scene diagnostics.

The issue's PR bodies call these presets zero-warning and show natural output heights above 900. Specification 50 permits natural canvas growth, so requested 1600 × 900 and larger actual SVG dimensions are not by themselves a failure. The warning-scope interpretation is material: under a strict Scene-diagnostic reading, no current PR qualifies for merge under the published [implementation plan](../../planning/active/issue-470-catalogue-preset-integration-implementation-plan-2026-09-26.md). A CLI-only reading would need an explicit approved acceptance interpretation; it cannot be silently substituted for the literal phrase. The responsible next action is to settle that interpretation, then either amend the design/plan and retest or fix the underlying diagnostics under their owning issues before serial merges.
