<!-- chrona:literal-acceptance/v1 -->

# Large-plan routing feedback acceptance

## Literal issue acceptance

### Issue #1723

- Source: [Issue #1723](https://github.com/tya5/chrona/issues/1723)
- Observed: 2026-10-18

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | A profile summary on the issue, then the chosen change with before/after times for 120, 240 and 400 tasks on one machine. | met | [Profile and selected algorithm](https://github.com/tya5/chrona/issues/1723#issuecomment-6250681409); [same-host comparison and stop decision](https://github.com/tya5/chrona/issues/1723#issuecomment-6251104681). The candidate is rejected: no convincing end-to-end gain. All three outputs and diagnostics match. No numeric speed target or routing speedup is claimed. | — |
| 2 | A synthetic large plan triggers the cost warning; `--progress` prints to a non-TTY stderr. | met | [Early CLI and completed MCP feedback](../../../tests/unit/chrona/app/test_routing_cost_feedback.py), [selected multiplicity admission](../../../tests/unit/chrona/presentation/layout/test_routing_workload.py), [captured subprocess progress](../../../tests/integration/test_render_progress_cli.py). The warning names both `--relations none` and `relationRouting`. | — |
| 3 | The MCP guide's speed claim matches the measured behaviour. | met | [Corrected guide](https://github.com/tya5/chrona/blob/3ee4d0fec82c2008b3c88cdc90c52a625fbbcfa4/docs/guides/agent-interface.md) from merged [PR #1730](https://github.com/tya5/chrona/pull/1730); this branch follows that ready main. Large-plan routing is explicitly not a few-second promise. | — |

## Architecture and verification

Pre-code [advisory design and architecture review](https://github.com/tya5/chrona/issues/1723#issuecomment-6250903952)
publishes Specs33/50 at `34d24909a`; implementation is `1870648ec`.
The equivalent-geometry candidate `d3b7c705e` was measured and removed under
its published stop condition, rather than accumulating unhelpful tuning.
Routing algorithms, budgets, order and suppression policy remain unchanged.
Routing still takes about nineteen minutes on the measured 400-task input.

Layout estimates potential endpoint pairs from selected facts; Model carries
the typed advisory, the existing best-effort observer provides early feedback,
and CLI/MCP share the final warning formatter. Scene infers no workload or
routing policy. The inclusive336-pair threshold is calibrated to the measured
240-task input, not borrowed from a timeout or used as a performance promise.
Small quiet renders retain their bytes; explicit non-TTY phase progress remains.

Focused observer/usecase17, feedback/message/skill68 and all10 subprocess
progress tests pass. After rejecting the geometry candidate, obstacle,
workload, typed-advisory and CLI/MCP feedback checks pass33. The import-direction
guard passes. No local full suite or additional corpus sweep was run.

PR run39138383520 exposed the same integer-count expression in conformance
and pytest shard1: the geometry accumulation guard cannot classify a sum of
endpoint multiplicity products. Explicit integer accumulation preserves the
count and warning threshold without weakening that guard; focused workload
and guard tests pass20.

## Programme-level criteria (optional)

PR1731 merged `b5f5e24b57bbcafbcde8f158bb153149c7ff85a8`; final
[CI39139341764](https://github.com/tya5/chrona/actions/runs/39139341764)
passes. Exact artifact12140942825 retains all50 SVG/50 Scene bytes; only
diagnostic source locations change. Exact-main native
[release39140760742](https://github.com/tya5/chrona/actions/runs/39140760742) on
`5f93db26707b6ca3695c05ef281d93666a60a060` passes all three OS matrices,
MCP floor and newest-Python public reproduction.

The additional design-only [review request](https://github.com/tya5/chrona/issues/1723#issuecomment-6251245796)
is addressed by the published [three-option comparison and architecture review](https://github.com/tya5/chrona/issues/1723#issuecomment-6252067725).
It distinguishes existing default first-fit/relax, critical-first and hint
reuse from new work; unknown gains are not invented. Reviewer disposition
remains pending. No algorithm implementation is authorized;
issue1723 stays open.
