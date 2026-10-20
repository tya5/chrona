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
| 3 | The late run on the timeline starts after the deadline day, with no 1-day stub for on-time work. A count table for public slides (expected: slides with deadlines exactly on the finish change). | met | Actual [SVG on-time/one-day tests](../../../tests/integration/test_deadline_mark.py) prove span/point runs start after the deadline and no on-time stub is emitted. [Official public count audit](https://github.com/tya5/chrona/pull/1844#issuecomment-6296962743): all50 SVG/Scene pairs byte-identical, zero changed routes/labels/marks/diagnostics; none of those public Scenes contains an active deadline glyph. Synthetic actual SVG/forecast/message fixtures prove the positive migration rather than attributing it to this corpus. | — |

## Programme-level criteria (optional)

Local focused batches overlap: Core/Layout/forecast/folded/network/actual SVG
and PDF checks 131 passed; terse/CLI deadline subset 17 passed; import direction
11 packages/37 inward edges. Tests include zero-extent rollups at `date.min`,
completed ordinal boundaries beyond `date.max`, and explicit-window admission.
No public-corpus source/generated evidence was authored. PR1844 at
`1595f0c82bed87e8e063e9f334d1f99f13440ef2` passed all applicable
[CI39464378020](https://github.com/tya5/chrona/actions/runs/39464378020)
checks and merged as `f491f8d5ea7bd450e97019a7df07c615443313cf`.
The official109-path snapshot changes only74 diagnostic source anchors;
all50 actual SVGs and50 Scenes retain their bytes. Exact review-containing
main three-OS release is still required before issue closure.
