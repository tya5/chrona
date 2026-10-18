<!-- chrona:literal-acceptance/v1 -->

# Guided workspace lifecycle acceptance

## Literal issue acceptance

### Issue #1725

- Source: [Issue #1725](https://github.com/tya5/chrona/issues/1725)
- Observed: 2026-10-19

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | A copied target-b and a copied default preset both render through `render-workspace` and the MCP render tool. | met | [CLI twins](../../../tests/cli/test_cli_guided_render.py), [MCP twins](../../../tests/unit/chrona/app/test_agent_workspace_lifecycle.py), and [shared use case](../../../tests/unit/chrona/usecases/test_guided_render.py) render both locally copied presets. | — |
| 2 | A Japanese title survives an edit as readable text, and key order is unchanged. | met | [Authoring writer regression](../../../tests/unit/chrona/operational/test_authoring_commands.py) and [real stdio lifecycle](../../../tests/mcp/test_workspace_lifecycle_stdio.py) check readable Japanese source and original project key order after forward/inverse edits. Both presets' actual Japanese PNGs were inspected locally. | — |
| 3 | An MCP-only scripted agent (stdio test) creates a workspace, validates it, edits it, reverts it and renders it with no CLI call and no hand-read revision. | met | [Real stdio lifecycle](../../../tests/mcp/test_workspace_lifecycle_stdio.py) uses only tool calls and returned revisions for creation, validation, revision query, inline forward/inverse edits and rendering, for both presets. | — |
| 4 | The agent-interface guide matches the tool list, checked by a docs test that reads the server's tool registry. | met | [Registry-reading guide test](../../../tests/unit/tools/test_agent_interface_guide.py) compares all 13 tools, titles and write annotations, and checks current authoring/revert/revision guidance. | — |

## Architecture and verification

Implementation: `2a14a6689`; strict-YAML closure correction: `3e4541198`.

The [pre-code plan](https://github.com/tya5/chrona/issues/1725#issuecomment-6250424023)
and [architecture review/implementation plan](https://github.com/tya5/chrona/issues/1725#issuecomment-6250489534)
publish Specs51/66 at `517d90e91` and `1ac627b6a` before implementation.
Ordinary and guided Draft share preset acquisition; the normalizer alone reads
guided syntax, and both CLI/MCP use one guided-render use case and the existing
render pipeline. Initialization validates a private candidate before exclusive
new-directory publication. Rollback removes only newly owned files; existing
edits retain their original CAS/replay engine. No Layout, Scene, adapter,
packaged design or schema file is changed. Two independent reviews found no
blocking responsibility or publication-safety defect.

Focused authoring/guided/Draft checks passed (81, then 17); existing MCP/Store
checks passed (107). Final import-direction/startup instruction checks passed
67 tests. The exact diagnostic code, detail and source pointer are checked
separately (64 focused tests). Final CLI/MCP lifecycle and guide tests pass14.
The documented-command reference and import-direction guards pass.
Initial CI39133011499 found the effective-View mapping subclass could not be
YAML-serialized and the review lacked its required programme-section heading;
both are corrected. The shared closure emits plain documents before guided
normalization, retaining provenance on the typed sources. Strict-YAML and
isolated Python3.11 stdio target-b regression checks pass.
Later CI exposed an overbroad structural-test substring and a stale packaged
tool table; exact AST guards and registry-derived coverage correct both.
CI39134683708 passes shards1/2 and fails only the skill's 200-line limit in
shard3. Moving MCP-only guidance to a linked reference keeps the entrypoint at
199 lines without removing lifecycle rules; all44 packaged-skill tests and
the skill validator pass. The test limit is unchanged.

## Final release

PR [#1730](https://github.com/tya5/chrona/pull/1730) merged as
`063fc97e2c7e1de541598c80a323c8d93e55c329`; final PR CI
[39136788182](https://github.com/tya5/chrona/actions/runs/39136788182) passed.
Official artifact `12140545789` was reviewed: all 50 SVG and 50 Scene files
are byte-identical; only declared diagnostic/source-position evidence changed.
The literal review is present on exact ready main
`3ee4d0fec82c2008b3c88cdc90c52a625fbbcfa4`. Native release
[39138121367](https://github.com/tya5/chrona/actions/runs/39138121367) passed
full pytest, conformance and wheel checks on Ubuntu, macOS and Windows, plus
oldest-MCP stdio and newest-Python materializer reproduction. All four literal
rows are met, with none deferred. See the [closing acceptance
comment](https://github.com/tya5/chrona/issues/1725#issuecomment-6251828895).
