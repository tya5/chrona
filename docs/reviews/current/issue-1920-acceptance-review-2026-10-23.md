<!-- chrona:literal-acceptance/v1 -->

# Literal acceptance review: #1920 rows 1 to 3

Observed on `main` at `e3ec09e9f` (the derived-sync bot commit after [PR #1933](https://github.com/tya5/chrona/pull/1933)). [Issue #1920](https://github.com/tya5/chrona/issues/1920) is the follow-up of the `narrowed` row 1 of [#1892](https://github.com/tya5/chrona/issues/1892). It has three bullets under `Acceptance:` and one comment (dev B's status of 2026-10-22, which restates the same three rows and the rule); the body and the comment were re-fetched with `gh issue view 1920 -R tya5/chrona --json body,comments` on 2026-10-23 and counted literally: three rows. Landed: [PR #1926](https://github.com/tya5/chrona/pull/1926) (`8a43b9162`). Rows 1 and 2 are `met`. Row 3 is `narrowed`: the guide and Spec 66 section 2.5 list the six new types by name, but the `SKILL.md` table row names the covered members ("every Project member except `version`, including extensions") and not the command types.

## Method

Private venv `/private/tmp/claude-501/venv1682`, `PYTHONPATH=<worktree>/src:<worktree>:<worktree>/packages/chrona-fonts-noto-cjk/src`, worktree on `origin/main` `e3ec09e9f`. Tests: [pytest-1920.txt](assets-1920/pytest-1920.txt) (87 passed: `test_project_command_coverage.py`, `test_agent_project_inverse.py`, `test_agent_project_extension_commands.py` and `test_schema_identifiers_and_license.py`) and [pytest-1920-guide.txt](assets-1920/pytest-1920-guide.txt) (`test_agent_interface_guide.py`, 1 passed). The documents were read with `grep` for the six type names.

## Literal issue acceptance

### Issue #1920

- Source: [Issue #1920](https://github.com/tya5/chrona/issues/1920)
- Observed: 2026-10-23

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | every top-level Project schema member except `version` has a command type (the coverage test's `NOT_COVERED` holds only `version`); | met | `NOT_COVERED` in [`test_project_command_coverage.py`](../../../tests/unit/chrona/app/test_project_command_coverage.py) (lines 18 to 20) holds only `version`, and the test asserts that the schema members equal the union of `COMMANDS` and `NOT_COVERED` with no overlap and no empty reason. It passes ([log](assets-1920/pytest-1920.txt)). The commands are `setExtension` / `removeExtension`, `setPeriod` / `removePeriod`, `setScenario` / `removeScenario` in [`project_commands.py`](../../../src/chrona/usecases/project_commands.py) and the enum of [`project-command-v0.1.schema.yaml`](../../../schemas/project-command-v0.1.schema.yaml); `test_extension_period_and_scenario_commands_round_trip` ([`test_agent_project_extension_commands.py`](../../../tests/unit/chrona/app/test_agent_project_extension_commands.py)) applies them through the tool. | — |
| 2 | apply -> inverse restores identical bytes for the new types (extend the table-driven test); | met | The table of `test_apply_then_inverse_restores_the_exact_file_bytes` ([`test_agent_project_inverse.py`](../../../tests/unit/chrona/app/test_agent_project_inverse.py), line 121) has cases for all six new types, each compared byte for byte after apply and inverse: `setPeriod` replace / new / new before / new in a new member, `removePeriod` first / sole, `setScenario` replace / new / new in a new member, `removeScenario` first / sole, `setExtension` replace / new / new at index / new in a new member, `removeExtension` first / sole (17 new cases), all passed ([log](assets-1920/pytest-1920.txt)). | — |
| 3 | the SKILL.md table row, the agent-interface guide and Spec 66 sec 2.5 list the new types. | narrowed | The guide lists all six by name with their payloads ([`agent-interface.md`](../../../docs/guides/agent-interface.md), lines 263 to 267) and Spec 66 section 2.5 does too ([`66-agent-interface.md`](../../../docs/specification/66-agent-interface.md), lines 300 to 306); the guide test passes ([log](assets-1920/pytest-1920-guide.txt)). The `SKILL.md` row of `apply_project_command` was changed to "Edits `project.yaml` (every Project member except `version`, including extensions) ... the accepted result's `inverse` reverts it": it names the members now covered, as the row did before ("objects, relations, ..."), and does not name the command types; `grep` finds none of `setExtension`, `setPeriod`, `setScenario` under `skills/` (the skill is held at 200 lines, which the PR cites as the reason). So two of the three documents list the types and the third states the coverage without the type names. | [`SKILL.md` row of `apply_project_command`](../../../skills/chrona/SKILL.md) (no follow-up issue is filed; a reviewer decision whether the member wording is enough) |

Counts: 3 rows, 2 `met`, 1 `narrowed`, 0 `not met`.

## Programme-level criteria (optional)

### Public side effects

This review adds a document and logs under [assets-1920](assets-1920/pytest-1920.txt); it changes no code, schema, specification, guide, preset, design, example or workflow.

| Item | Slides changed | New diagnostics | Schema delta |
| --- | ---: | ---: | --- |
| This review | 0 | 0 | none |

The public effect of the reviewed PR is in its own body: 0 slides, 9 new diagnostic codes, `project-command-v0.1` enum plus 6 values (additive).
