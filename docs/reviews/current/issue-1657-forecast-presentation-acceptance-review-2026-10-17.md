# Issue1657 — forecast presentation acceptance

<!-- chrona:literal-acceptance/v1 -->

The [work record](../../planning/active/issue-1657-forecast-presentation-work-record-2026-10-17.md)
links the pre-code design, architecture review and implementation plan.
View owns per-occurrence label eligibility; application classification preserves
Scheduler evidence; the shared warning ledger supplies Scene/CLI parity.
No examples or generated artifacts were edited.

## Literal issue acceptance

### Issue #1657

- Source: [issue](https://github.com/tya5/chrona/issues/1657)
- Observed: 2026-10-17

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| --- | --- | --- | --- | --- |
| 1 | Synthetic twin: with `--forecast`, one member label per object; the ghost has none. | met | [Render tests](../../../tests/unit/chrona/usecases/test_forecast_render.py) retain Snapshot ink and required deltas; [occurrence tests](../../../tests/integration/test_forecast_label_ownership.py) cover automatic, explicit, lane and folded rows, plus a non-forecast control. | — |
| 2 | Synthetic twin: an observed start one day before the predecessor's finish gives the forecast warning, and no `E_FIXED_TARGET_VIOLATION`. | met | [Scheduler tests](../../../tests/unit/chrona/usecases/test_forecast_schedule.py), [transport test](../../../tests/unit/chrona/usecases/test_forecast_warning_transport.py) and end-to-end render test prove retained dates, truthful warning severity/details and Scene/CLI identity; malformed evidence and genuine scheduling errors remain errors. | — |
| 3 | Trial command above on technical-print: one label per bar, viewed as PNG. | met | Exact [immutable trial3](https://github.com/tya5/chrona/tree/dbbce45e60392b7b0be788f841fe2673f4830944/trial3) command rendered and PNG viewed. Scene member labels44→22, exactly one for each22 objects; Snapshot primitives25→25 and required forecast deltas22→22. Observed November9/November10 overlap warns with overlapDays=1, not the former fixed-target code. | — |
| 4 | Public SVG/Scene changes listed with counts. | met | [PR1662 official snapshot39036008847](https://github.com/tya5/chrona/actions/runs/39036008847) on `f6e245aa7`: identical109 paths, all50 SVG+50 Scene files byte-identical, no public primitives/routes/labels added, removed or changed. Only diagnostic inventory changes (304211→304383 bytes); other8 reports unchanged. | — |

## Programme-level criteria (optional)

The combined focused scheduling, warning, render/occurrence, projection and
lane-label batch passes118 tests; the added end-to-end warning test passes.
All four literal rows have focused/artifact evidence. Exact review-containing
main three-OS full pytest/conformance/wheel, reproduction and MCP release gates
remain pending. Keep issue1657 open until those gates are complete.
