<!-- chrona:literal-acceptance/v1 -->

# Docs ready-base acceptance (#1385)

Implementation: `5ebc5af1b94ceed2d36cf721846c246770a4e369`, on trusted READY `8e7300c0` before ordinary adoption of the next ready main. Design and whole-architecture review: [current work record](https://github.com/tya5/chrona/issues/1385#issuecomment-6102066186).

## Literal issue acceptance

### Issue #1385

- Source: [Issue #1385](https://github.com/tya5/chrona/issues/1385)
- Observed: 2026-10-11

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | A test shows a docs-only diff on a ready-but-not-tip base passes the gate. | met | [Actual workflow execution](../../../tests/unit/tools/test_docs_derived_ready_gate.py): `test_docs_on_ready_non_tip_base_pass_without_sync_wait_or_tip_query` supplies different ready base/current tip, runs the workflow's Bash gate and verifies success. | — |
| 2 | A diff touching a derived-owned docs path, or any code path, still requires the ready tip. | met | [Gate tests](../../../tests/unit/tools/test_docs_derived_ready_gate.py) classify and execute every shared generated-report path and a code path: all non-tip bases fail; exact ready code passes. [Classifier tests](../../../tests/unit/tools/test_classify_ci_change.py) prove generator/classifier use the same inventory and the no-install CI entry point works. | — |
| 3 | `derived-ready` runtime for docs PRs no longer includes waiting for a new sync. | met | [Workflow execution](../../../tests/unit/tools/test_docs_derived_ready_gate.py) completes within its 5-second test timeout with one trusted-base query, no sleep and no current-tip query; missing/failed/pending readiness fails immediately, not by waiting. | — |
| 4 | Do not edit `examples/**`. | met | [Implementation commit](https://github.com/tya5/chrona/commit/5ebc5af1b94ceed2d36cf721846c246770a4e369) edits only CI, tool ownership inventory, AGENTS and synthetic tests. | — |

## Programme-level criteria (optional)

Release pending: fresh PR snapshot/current-head gates and exact published-main three-OS release containing this review are required before closure.

## Architecture conclusion

CI-only change: the dependency-free report authority is consumed by the generator and classifier; no copied ownership list, generated edits, product/resource/schema changes, sync retirement changes or release-gate exemption. Docs require successful own dependency outcomes, current head, main base, affirmative mergeability and latest trusted base readiness; unknown/failure fails closed. Code retains bounded readiness polling and its final exact-tip check. Workflow tests use the shared Actions-compatible Bash selector and shell-function stand-ins, including Windows Git Bash, without external API calls. Full three-OS release remains mandatory.

Focused classifier/gate/conformance-workflow/derived-evidence/workflow batch: **60 passed (27.82s)**. Trusted-gate/cleanup regression batch: **52 passed (7.90s)**.
