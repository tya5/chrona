# Gallery freshness and viewport survey review

<!-- chrona:literal-acceptance/v1 -->

Design, architecture and implementation plan: [living record](https://github.com/tya5/chrona/issues/1474#issuecomment-6158249825).
Published source: [PR1491](https://github.com/tya5/chrona/pull/1491),
main7b4796e79a001970344d31ea51fa9aa680d44b68; trusted gate38571167171PASS.
Tool repair d0108cd4 follows the independently published fixes in PR1483/1484.
[Reviewer disposition](https://github.com/tya5/chrona/issues/1474#issuecomment-6167307115):
keep all capacity cases with exact expected diagnostic outcomes; defer core
allocation changes to #1490. On exact published main7b4796e7, both full API
and CLI --jobs4 accept all138 cases:117 render,21 give their recorded refusal,
0 unexpected outcomes (exit0); gallery --check passes. The checkout matches
origin/main before and after, with its own verified venv import.
Focused tool tests15PASS; review/ledger tests7PASS. No product, examples or
generated-output changes in this remaining slice. [PR CI38569397029](https://github.com/tya5/chrona/actions/runs/38569397029)
passes. Snapshot11897795293: all101 members byte-identical, no added/removed
paths. Independent implementation/architecture review found no gap.
Containing-review [release38575019372](https://github.com/tya5/chrona/actions/runs/38575019372)
on exact7f0c9c50d950a5d0517872c3170ab95aedcaf447 passes all three OS full
pytest/conformance/wheel-smoke jobs, newest-Python public materializers and MCP.
After dev B PR1492, exact main24374ec8 was revalidated: API/CLI117 rendered,
21 exact expected refusals,0 failures; gallery check passes, checkout unchanged.
Issue1474 is closed. PR1494's initial readiness-only failure was
[dispositioned](https://github.com/tya5/chrona/pull/1494#issuecomment-6169786499);
the revalidated gate passed on attempt2 without a workflow change or bypass.
Architecture: expectations belong to the validation tool, not Layout policy.
API and CLI share the existing failure reporter's complete diagnostic payload
and exit code; no synthetic domain code or project-specific core exception.

## Literal issue acceptance

### Issue #1474

- Source: [issue](https://github.com/tya5/chrona/issues/1474)
- Observed: 2026-10-14

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| --- | --- | --- | --- | --- |
| 1 | Both tools pass on main. | met | [Exact-main verification](https://github.com/tya5/chrona/issues/1474#issuecomment-6158249825): main7b4796e7, API and CLI117/138 rendered +21 exact expected refusals,0 failures, exit0; gallery --checkPASS. [Recorded outcomes](../../../tools/draft_viewport_expected_refusals.yaml) retain every case and link each group to #1490. [Tests](../../../tests/unit/tools/test_check_draft_viewport_matrix.py) reject changed code/message/source/component/exit, unexpected rendering, unlisted failures and missing cases. | — |
| 2 | Each is either in the CI gate or explicitly documented as manual. | met | Gallery remains in [conformance registration](../../../conformance/run_conformance.py). [CONTRIBUTING](../../../CONTRIBUTING.md) and the [tool docstring](../../../tools/check_draft_viewport_matrix.py) explicitly require the manual matrix when changing Layout allocation; no additional CI shard or duplicated whole-corpus PR run. | — |
| 3 | Do not edit `examples/**`. | met | [Final source diff](https://github.com/tya5/chrona/compare/930b82459d34c46b29e0e593c967d9e620ab8687...cc8c5a4dac54b7091b380d91693507c5a509b2f5) has no examples edits. [Earlier repairs](https://github.com/tya5/chrona/compare/1299e952a22d855f81d04f32b5ad81ff0f462da8...0fa35d73) likewise preserve examples. [Identity tests](../../../tests/unit/tools/test_check_draft_viewport_matrix.py) preserve authored bytes/snapshot/assets; derivative Contexts are temporary and truthfully pinned. | — |

## Programme-level criteria (optional)

None.
