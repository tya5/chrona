# Scheduled conformance admission review

<!-- chrona:literal-acceptance/v1 -->

Design/architecture/plan: [living record](https://github.com/tya5/chrona/issues/1340#issuecomment-6157659345).
Implementation3a041961 on READY1299e952. One workflow admission owner freezes
main and validates its latest trusted exact-SHA check; consumers do not select,
regenerate or substitute evidence. Default dispatch and the trusted publication
protocol are unchanged.28 focused/adjacent workflow tests pass. The actual
two-call read-only smoke selected1299e952. No examples or derived outputs edited.
PR and containing-review exact-main release gates remain required before closure.

## Literal issue acceptance

### Issue #1340

- Source: [issue](https://github.com/tya5/chrona/issues/1340)
- Observed: 2026-10-14

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| --- | --- | --- | --- | --- |
| 1 | A synthetic scheduled-start-during-sync case cannot run reproduction/full matrix against unready source evidence. | met | [Selector tests](../../../tests/unit/tools/test_scheduled_readiness.py) reject source-only current main without fallback; [workflow test](../../../tests/unit/tools/test_conformance_workflow.py) requires successful admission before any of the three consumers run. | — |
| 2 | Every scheduled full-matrix, newest-Python and MCP job uses the same immutable validated SHA; advancing main cannot produce mixed checkout bases. | met | [Selector tests](../../../tests/unit/tools/test_scheduled_readiness.py) advance main after the single ref read and retain the frozen SHA. [Workflow tests](../../../tests/unit/tools/test_conformance_workflow.py) assert all three checkouts use that one output. | — |
| 3 | Missing/failed readiness has explicit bounded failure or defer behavior, not a silently accepted stale run. | met | [Selector/transport tests](../../../tests/unit/tools/test_scheduled_readiness.py) cover missing/pending/latest failed/untrusted/truncated responses, HTTP failure, invalid JSON and timeouts; explicit GET, at most2 calls of30s, job bound2min. No ancestor scan, polling or per-job generation. | — |
| 4 | PR snapshot and exact-SHA post-sync dispatched release behavior remain unchanged. | met | [Workflow tests](../../../tests/unit/tools/test_conformance_workflow.py), [gate cleanup tests](../../../tests/unit/tools/test_derived_gate_cleanup_workflow.py): default event-SHA pass-through, unchanged PR snapshot jobs, exact expected_sha guard; manual ready selection cannot combine with expected_sha. | — |
| 5 | Record an actual scheduled/manual-equivalent run on a ready SHA with public materializer and full-matrix evidence. | not met | [Actual opt-in manual-equivalent run38492865692](https://github.com/tya5/chrona/actions/runs/38492865692), control workflow3a041961: admission has succeeded; full three-OS/MCP/newest-Python consumers are still live. Verify its frozen SHA and completed outcomes before accepting this row. | — |

## Programme-level criteria (optional)

None.
