<!-- chrona:literal-acceptance/v1 -->

# Issue 1426 — routing performance and budget acceptance

Implementation: [PR1428](https://github.com/tya5/chrona/pull/1428), reviewed head
`152d196416eaa530264fff5c09de1b76746eddca`, source merge
`2ba414f2a86ff66dd236a3f7bf6d96bd1b153a4b`.
[Head CI](https://github.com/tya5/chrona/actions/runs/38194676311) passed all
three pytest shards, conformance, newest-Python reproduction, MCP floor and readiness.
Artifact11722837924 contains46 parsed, unchanged Scene/SVG pairs, no additions
or retirements; only the diagnostic code-site inventory changes.
Release acceptance remains pending repeat completion and exact-main full CI
containing this review. Keep the issue open.

## Literal issue acceptance

### Issue #1426

- Source: [issue1426](https://github.com/tya5/chrona/issues/1426)
- Observed: 2026-10-12

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | Every example Scene and SVG is byte-identical without `searchBudget`. | met | [Current-head artifact audit](https://github.com/tya5/chrona/pull/1428#issuecomment-6116600979):46/46 complete pairs unchanged; real materializers also46/46, without normalization overrides. | — |
| 2 | A test: a relation that reaches its budget is reported with its id and pass, and handled by suppression (later by #1427). | met | [Synthetic Scene/CLI/suppression tests](../../../tests/integration/test_declared_relation_budget.py); [per-pair accounting](../../../tests/unit/chrona/presentation/layout/test_relation_search_budget.py), rejected rehearsal/recovery facts and immutable receipts. | — |
| 3 | The three trial inputs are re-measured. The 1000/228 CPU time is reported against the 60 s budget. | met | [Measurement report](https://github.com/tya5/chrona/issues/1426#issuecomment-6116658178):19/10 CPU1.48/1.66s;200/46 CPU32.056357/31.160932s;1000/228 first CPU813.344333s, wall964.490813s, RSS216743936 bytes, exit0. Second1000 repeat is pending. | — |
| 4 | Do not edit `examples/**`. | met | [Reviewed diff](https://github.com/tya5/chrona/pull/1428/files): authored examples/resources unchanged; CI produces the disposable managed snapshot. | — |

## Programme-level criteria (optional)

The measured1000/228 time is13.56x60s: **M2's time target is not met**.
Earlier53s results were first-fit, not retained-policy evidence. Reporting the
literal measurement criterion does not prove the programme-level performance target.

## Architecture and release disposition

Exact bound, histories, quotas, candidate order/ranking and label passes remain
unchanged. Layout owns the per-instance/per-pass counter and completed facts;
Scene/CLI project them. Contrast inspection reuses private immutable classifications,
not layout geometry. No abandoned policy declaration or approximate search remains.
The independent annotation compaction fix retains the same46 public artifacts.
