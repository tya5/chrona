<!-- chrona:literal-acceptance/v1 -->

# Issue 1840 — inclusive deadline days

Pre-code design/specification correction `d50544d4b`; implementation
`c5e768dc4`. [Current plan and architecture review](https://github.com/tya5/chrona/issues/1840#issuecomment-6295660794).
Core owns one inclusive planned/forecast verdict and integer day boundaries;
View carries completed facts, Layout maps/clips them, and Scene/adapters do not
interpret dates. Scheduler endpoints, dependencies and bounds are unchanged.
Point verdicts stay unchanged; point late-run geometry intentionally represents
full late calendar days. Two independent reviews found no remaining owner gap.

## Literal issue acceptance

### Issue #1840

- Source: [Issue1840](https://github.com/tya5/chrona/issues/1840)
- Observed: 2026-10-21

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | A synthetic test: finishing on the deadline is on time; finishing one day after is 1 day late; the forecast path gives the same result. | met | [Core planned/forecast tests](../../../tests/unit/chrona/core/test_deadlines.py), [SVG span/point tests](../../../tests/integration/test_deadline_mark.py), and [forecast rendering](../../../tests/integration/test_forecast_deadlines.py). | — |
| 2 | The message and `details.finish` show the inclusive date. | met | Exact [Core warning assertions](../../../tests/unit/chrona/core/test_deadlines.py), [render ledger](../../../tests/integration/test_deadline_render.py), and two regenerated [CLI records](../../../tests/fixtures/cli_characterization/golden.json); all other CLI record fields unchanged. | — |
| 3 | The late run on the timeline starts after the deadline day, with no 1-day stub for on-time work. A count table for public slides (expected: slides with deadlines exactly on the finish change). | not met | Actual [SVG on-time/one-day tests](../../../tests/integration/test_deadline_mark.py) pass; official public-slide count/visual audit is still pending. | — |

## Programme-level criteria (optional)

Local focused batches overlap: Core/Layout/forecast/folded/network/actual SVG
and PDF checks 131 passed; terse/CLI deadline subset 17 passed; import direction
11 packages/37 inward edges. Tests include zero-extent rollups at `date.min`,
completed ordinal boundaries beyond `date.max`, and explicit-window admission.
No public-corpus source/generated evidence was authored. Public artifact audit,
PR CI and exact review-containing main three-OS release remain required.
