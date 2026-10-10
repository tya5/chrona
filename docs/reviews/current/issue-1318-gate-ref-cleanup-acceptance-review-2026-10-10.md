<!-- chrona:literal-acceptance/v1 -->

# Issue #1318 — temporary gate ref cleanup

Implementation: `d49846566edd3f203fb6d8a9a228b822cbaa4dcc`;
[PR #1359](https://github.com/tya5/chrona/pull/1359) merged as
`85ff5e4460cb1827127630467efb2807513186ce` on ready parent `d92c2294`.
All [exact-head PR checks](https://github.com/tya5/chrona/actions/runs/38057992838)
passed. Root and independent review verified artifact `11672240441`: all 101
paths (46 Scenes/46 SVGs included) are byte-identical to the exact base.
[Current design, architecture and plan](https://github.com/tya5/chrona/issues/1318#issuecomment-6093049623).
Normal-sync and real sweep acceptance are proved below. Final-review-containing
exact-main three-OS release remains required; do not close yet.

## Literal issue acceptance

### Issue #1318

- Source: [Issue #1318](https://github.com/tya5/chrona/issues/1318)
- Observed: 2026-10-10

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | After a sync completes, its gate branch is gone. The sweep removes a planted stale gate branch and leaves one whose run is in progress. | met | [Normal sync](https://github.com/tya5/chrona/actions/runs/38059206825/job/114233832004) succeeds, including terminal-gate consumption, exact-SHA release dispatch and cleanup; candidate `85ff5e44` ref subsequently returns HTTP 404. [Actual scoped real-API sweep](https://github.com/tya5/chrona/issues/1318#issuecomment-6093049623), using published helper bytes, deletes only planted historic `e1a6f812` after trusted37958301088 completes and preserves `ddbf4ceb` during trusted38050993391 in progress; absence/retention rechecked. [Workflow safeguards](../../../tests/unit/tools/test_derived_gate_cleanup_workflow.py) pass. Cron wiring tested, not claimed executed. | — |
| 2 | Do not edit `examples/**`. | met | [Owned implementation](https://github.com/tya5/chrona/commit/d49846566edd3f203fb6d8a9a228b822cbaa4dcc) changes tooling/workflow, contributor procedure and synthetic tests only. | — |

## Programme-level criteria (optional)

Focused cleanup/workflow/trusted-gate/conformance/tooling batch: 61 passed (12.60s).
Trusted gate [38059507802](https://github.com/tya5/chrona/actions/runs/38059507802)
and normal sync succeeded on exact `85ff5e44`; no generated delta or fast-forward
was needed. Release [38060021623](https://github.com/tya5/chrona/actions/runs/38060021623)
was dispatched on that SHA; [Ubuntu checkout and exact-SHA verification](https://github.com/tya5/chrona/actions/runs/38060021623/job/114236206257)
both succeeded despite deletion of the temporary ref. The running matrix is
not yet release acceptance.
Unknown/active/incomplete gates remain preserved; only HTTP 404 is idempotent.
Deletion relies on immutable refs and the serialized non-cancelling queue;
REST deletion is not compare-and-swap against an external manual repoint.
Final review publishes with the next coherent #1291 unit; its exact-main
three-OS conformance/pytest/wheel result is required before closure.
