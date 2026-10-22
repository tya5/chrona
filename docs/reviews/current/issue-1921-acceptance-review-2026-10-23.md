<!-- chrona:literal-acceptance/v1 -->

# Literal acceptance review: #1921 rows 1 to 3

Observed on `main` at `e3ec09e9f`, which is the derived-sync bot commit after [PR #1933](https://github.com/tya5/chrona/pull/1933) (`24fba07ce`). [Issue #1921](https://github.com/tya5/chrona/issues/1921) is the follow-up of the `narrowed` row 2 of [#1892](https://github.com/tya5/chrona/issues/1892). It has three bullets under `Acceptance:` and no comment; the body and comments were re-fetched with `gh issue view 1921 -R tya5/chrona --json body,comments` on 2026-10-23 and counted literally: three rows. Landed: [PR #1933](https://github.com/tya5/chrona/pull/1933). Rows 1 and 3 are `met`. Row 2 is `narrowed`: every authoring command type has an inverse except `materializePresentationPreset`, which is declared irreversible (`reversible: false`) and which the PR records as "the one exception".

## Method

Private venv `/private/tmp/claude-501/venv1682`, `PYTHONPATH=<worktree>/src:<worktree>:<worktree>/packages/chrona-fonts-noto-cjk/src`, worktree on `origin/main` `e3ec09e9f`. Tests: [pytest-1921.txt](assets-1921/pytest-1921.txt) (264 passed, 1 skipped: `test_agent_workspace_inverse.py`, `test_agent_tools.py`, `test_schema_identifiers_and_license.py`) and [pytest-1921-guide.txt](assets-1921/pytest-1921-guide.txt) (`test_agent_interface_guide.py`, the registry-versus-guide test, 1 passed). The one skip is `test_materialization_is_irreversible_and_carries_no_inverse`, which skips itself when the local materializer output differs from the pinned proof (`E_AUTHORING_MATERIALIZE_OUTPUT_PROOF`, the known local mismatch because the derived pipeline regenerates `examples/**`); that assertion was not exercised here.

## Literal issue acceptance

### Issue #1921

- Source: [Issue #1921](https://github.com/tya5/chrona/issues/1921)
- Observed: 2026-10-23

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | on a guided workspace, an agent saves a baseline and renders with it through MCP alone; | met | `test_a_workspace_baseline_is_saved_and_drawn_by_render_workspace` ([`test_agent_workspace_inverse.py`](../../../tests/unit/chrona/app/test_agent_workspace_inverse.py), line 207) calls only tools through `call_tool`: `create_workspace`, `save_baseline {project: "ws/workspace.yaml", name}` (writes `ws/baselines/week-1.yaml`, a `timeline/v0.7` Project that `validate_project` accepts; a repeat is a replay; a different content under the same name is `E_BASELINE_FILE_EXISTS`), `apply_authoring_command`, then `render_workspace` plain and with `snapshot` set to the baseline path; both are `ok` and the content identities differ. `test_render_workspace_refuses_a_baseline_of_another_project` covers the refusal. Both pass ([log](assets-1921/pytest-1921.txt)). | — |
| 2 | apply -> returned inverse restores the exact workspace bytes for every authoring command type, including an added task; | narrowed | Covered and passing: an added task (`test_an_added_task_is_undone_by_its_inverse`, `..._at_an_index_is_undone`), replaced and removed tasks, added / replaced / removed actuals including the only actual, a selected preset, and new / replaced / removed overrides (the 23 tests of the file that run, [log](assets-1921/pytest-1921.txt)); the command enum has `removeWorkspaceTask`, `removeWorkspaceActual` and `removePresentationOverride` ([`authoring-command-v0.1.schema.yaml`](../../../schemas/authoring-command-v0.1.schema.yaml), line 11). Not covered: `materializePresentationPreset` returns `reversible: false` and no `inverse`, by design and stated in Spec 66 ([`66-agent-interface.md`](../../../docs/specification/66-agent-interface.md), section 2.3, lines 220 to 222) and in the PR body; its test is the one skipped locally. The criterion says "every authoring command type", so this row is `narrowed` to seven of the eight types. | [Spec 66 section 2.3, the stated exception](../../../docs/specification/66-agent-interface.md) (no follow-up issue is filed; an owner decision whether materialization needs an inverse) |
| 3 | guide, skill and Spec 66 sec 2.3 updated; registry-vs-doc tests pass. | met | Updated by [PR #1933](https://github.com/tya5/chrona/pull/1933): the guide ([`agent-interface.md`](../../../docs/guides/agent-interface.md), the "Baseline" paragraph at line 216 and "Undo an added task" at lines 241 to 242), the skill ([`SKILL.md`](../../../skills/chrona/SKILL.md) line 112 and [`guided-workspaces.md`](../../../skills/chrona/references/guided-workspaces.md) lines 12 to 13) and Spec 66 section 2.3 ([`66-agent-interface.md`](../../../docs/specification/66-agent-interface.md), lines 220 to 232). `test_agent_interface_guide.py` and `test_agent_tools.py` (the tool registry with the new `snapshot` member of `render_workspace`) pass ([log](assets-1921/pytest-1921-guide.txt), [log](assets-1921/pytest-1921.txt)). | — |

Counts: 3 rows, 2 `met`, 1 `narrowed`, 0 `not met`.

## Programme-level criteria (optional)

### Public side effects

This review adds a document and logs under [assets-1921](assets-1921/pytest-1921.txt); it changes no code, schema, specification, guide, preset, design, example or workflow.

| Item | Slides changed | New diagnostics | Schema delta |
| --- | ---: | ---: | --- |
| This review | 0 | 0 | none |

The public effect of the reviewed PR is in its own body: 0 new MCP tools, 3 tools changed, 3 authoring command types added, 2 schema files changed additively, 0 new diagnostic codes.
