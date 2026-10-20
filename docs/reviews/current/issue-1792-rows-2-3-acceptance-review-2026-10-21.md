<!-- chrona:literal-acceptance/v1 -->

# Literal acceptance review: #1792 rows 2 and 3

Observed on `main` at `b5d780034`. [Issue #1792](https://github.com/tya5/chrona/issues/1792) has three numbered acceptance rows (body and all seven comments re-fetched with `gh issue view 1792 --json body,comments` on 2026-10-21; no row was added after the first reading). Row 1 belongs to dev A and is listed below with their evidence only. Rows 2 and 3 landed in [PR #1805](https://github.com/tya5/chrona/pull/1805) (merge `e9aeef54e`). The issue is already closed by the owner after exact-main release run [39382911887](https://github.com/tya5/chrona/actions/runs/39382911887); this review is the literal per-row record for rows 2 and 3.

## Method

Private venv, `PYTHONPATH=<worktree>/src:<worktree>`, no shared install, current `main`. Trial-9 inputs came from the evidence branch `reviewer/trial-9-inputs` (the `trial-9/mcp/agent.py` call sequence and the `trial-9/exec` recipe plan), extracted read-only into a temp directory and not committed. Tests run: `tests/unit/chrona/app/test_agent_workspace_lifecycle.py` and `tests/integration/test_executive_summary_guide.py` (13 passed together). The full suite was not run here; the exact-main release run above covers it.

## Literal issue acceptance

### Issue #1792

- Source: [Issue #1792](https://github.com/tya5/chrona/issues/1792)
- Observed: 2026-10-21

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | Base the threshold on the measured cost model from #1734's phase data, or on candidate work rather than pairs. State it in `diagnostics.md`. The 150-task input triggers the warning on target-b. | met | Dev A's row, not reviewed or claimed here. Their review is [issue-1792-routing-cost-acceptance-review-2026-10-20.md](../../archive/reviews/issue-1792-routing-cost-acceptance-review-2026-10-20.md) with measurements in [assets-1792 README](../../archive/reviews/assets-1792/README.md) and the [150-task receipt](../../archive/reviews/assets-1792/target-b-receipt.md): landed in PR #1796, threshold of 2,370 potential normal connector-port pairs, the 150-task render warns at 2,388. Their closing comment [6286049580](https://github.com/tya5/chrona/issues/1792#issuecomment-6286049580) accepts all three rows on exact-main release 39382911887. | — |
| 2 | Identity is checked at the command, and the agent-interface guide covers both flows. | met | Identity: [`_check_preset_identity`](../../../src/chrona/usecases/authoring_commands.py) runs inside `prepare_authoring_command` for `selectPresentationPreset`, before the candidate is written. The trial-9 call (id `marquee`, version `1`, path `preset/preset.yaml` copied from target-b, as in `trial-9/mcp/agent.py`) was driven through a real `chrona mcp --allow-write` stdio server on current main with [`mcp_preset_identity.py`](assets-1792/mcp_preset_identity.py); output [`mcp-preset-identity-output.json`](assets-1792/mcp-preset-identity-output.json): status `rejected`, `E_AUTHORING_PRESET_IDENTITY` ("binding id/version='marquee'/'1', but 'preset/preset.yaml' is preset 'chrona-builtin-target-b'/'1'"), `workspace_revision` equal to the creation revision, `workspace.yaml` bytes unchanged, `render_workspace` still `ok`, and a matching re-pin `chrona-builtin-target-b` accepted at the same revision. The issue observed the revision advancing and a later render failure; neither happens now. Tests (passed here): [`test_select_preset_refuses_a_binding_the_pinned_preset_cannot_render`](../../../tests/unit/chrona/app/test_agent_workspace_lifecycle.py) covers both an id mismatch and a version mismatch. Guide: [agent-interface.md](../../guides/agent-interface.md), sections "Switch preset" (checked binding, the `chrona-builtin-target-b` id, the `marquee` over `target-b` example, switch by `create_workspace` with the other builtin) and "Undo an added task" (no delete; recreate the workspace without the task, the old workspace stays unchanged). | — |
| 3 | The guide defines depth, the recipe works on both plan shapes, and the header uses a wording key. | met | Depth: [executive-summary.md](../../guides/executive-summary.md), paragraph "How `depth` counts": relative to the top-level rows; `0` top rows only, `1` adds direct children, `all` everything; a plan whose phases are top-level needs `depth: 0` and `depth: 1` there shows every task. Both shapes rendered from the guide's own recipe files in [assets-1792/exec](assets-1792/exec/nested-plan.csv): nested plan with depth 1 shows the programme row plus the two phases ([PNG](assets-1792/exec/nested-depth1-en.png)); grouped-only plan with depth 0 shows exactly the two phases ([PNG](assets-1792/exec/grouped-depth0-en.png)); the same grouped-only plan at depth 1 reproduces the issue's complaint, showing the tasks under each phase, as the guide warns ([PNG](assets-1792/exec/grouped-depth1-en.png)). All renders status `ok`, no diagnostics. Header: the recipe column is `header: {wording: column.task}` and renders `Task` in en-US ([PNG](assets-1792/exec/nested-depth1-en.png)) and `タスク` in ja-JP ([PNG](assets-1792/exec/grouped-depth0-ja.png)); `Work item` no longer appears. Tests (passed here): [`test_guide_depth_counts_from_the_top_level_rows_on_nested_and_grouped_only_plans`](../../../tests/integration/test_executive_summary_guide.py) and `test_guide_table_header_follows_the_render_locale` in the same file. | — |

## Programme-level criteria (optional)

### Public side effects

This review adds one document, one small Python driver, one JSON output and eight rendered or input files under `assets-1792/`; no source, preset or example changes.

| Item | Routes | Labels | Primitives | New diagnostics |
| --- | ---: | ---: | ---: | ---: |
| This review | 0 | 0 | 0 | 0 |

Limits, not hidden: row 2 was reproduced with the trial-9 command sequence on a smaller project than the trial's (three tasks instead of the trial plan), because the defect is independent of plan content. The `assets-1792` directory under `docs/archive/reviews/` belongs to dev A's row 1 and is unchanged. The existing `Work item` view in the trial-9 `exec` folder is an authored English id and is not the guide recipe.
