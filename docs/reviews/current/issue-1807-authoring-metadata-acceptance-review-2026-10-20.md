# Issue1807 — authoring metadata acceptance

Source `1e102af46aaaac29148dbd5103042801a55274e6` on ready base
`f6b3ce41daa35457df696c7b149825ca561dfb24`.
[Issue and reviewer acceptance](https://github.com/tya5/chrona/issues/1807);
[pre-code plan and architecture review](https://github.com/tya5/chrona/issues/1807#issuecomment-6284307287).
This is a metadata correction prompted by the real-host trial, not a failed
product mutation. Spec66/Spec51 and the canonical command schema are unchanged.

| Literal criterion | Status | Evidence |
| --- | --- | --- |
| Tool metadata presents a directly usable full version and target example, pinned against the canonical schema. | met locally; release pending | Both existing descriptions state `version: chrona/authoring-command/v0.1` and distinguish `workspace: guided/workspace.yaml` from `target: {kind: authoring-workspace, path: workspace.yaml}`. `test_agent_authoring_metadata_matches_command_version_and_path_forms` reads the live inline schema const and pins both descriptions to it. |
| Existing invalid-version/path refusals and valid inline authoring tests remain covered. | met locally; release pending | The same test checks both real-host mistakes at schema preflight, byte-identical files after each refusal, then accepts a valid inline command. Existing authoring and real-stdio gate/replay/stale-base/no-overwrite controls pass. |
| Record the correction as a UX/metadata fix, not a product mutation failure. | met | Only metadata prose and its regression test change; no schema/tool-set version, parser, CAS/replay, gate, annotation, rendering or layer ownership changes. |

Focused verification:11 passed (agent authoring, deterministic/closed registry
schema controls and `tests/mcp/test_authoring_stdio.py`); `git diff --check` passed.
No local full suite or public materializer sweep was duplicated. This is a
checkpoint, not release acceptance: integrate the final ready main after
PR1806/1808, then require current-head PR CI/artifact review and exact-main
three-OS release before closing issue1807.
