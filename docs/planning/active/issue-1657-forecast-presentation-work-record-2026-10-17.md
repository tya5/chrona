# Issue1657 — forecast label ownership and observed-start warnings

Status: design planning. Baseline: main `aabc5e894`, with unchanged product
source from trusted-ready `9f35dd457` after the legend fix.
[Issue1657](https://github.com/tya5/chrona/issues/1657) is the next dev A item;
issue1397's implemented slice is preserved separately and publications stay serial.

## Literal acceptance

1. Synthetic twin: with `--forecast`, one member label per object; the ghost has none.
2. Synthetic twin: an observed start one day before the predecessor's finish gives the forecast warning, and no `E_FIXED_TARGET_VIOLATION`.
3. Trial command above on technical-print: one label per bar, viewed as PNG.
4. Public SVG/Scene changes listed with counts.

The trial command is `chrona render project.yaml --actual actual.yaml --snapshot
baseline.yaml --forecast --preset technical-print --output fc.png`, using
[immutable trial3](https://github.com/tya5/chrona/tree/dbbce45e60392b7b0be788f841fe2673f4830944/trial3).
Before PNG inspection confirms duplicate primary/Snapshot names. The observed
wireframes→visual-design miss carries `E_FIXED_TARGET_VIOLATION` with info severity.

## Design plan

- Preserve Project/Actual/Snapshot facts, the ghost geometry and required
  forecast deltas. Decide explicit View-owned member-label eligibility per
  occurrence, separate from temporal paint; Layout must not infer source policy.
- Trace forecast findings through Scheduler, application, typed projection and
  the common warning ledger. Define actual warning severity and stable Scene/CLI
  identity, not merely a renamed diagnostic in the informational transport.
- Distinguish true FS overlap from SS/lag-only bound misses. Name each relation,
  observed date, source endpoint/date, required date and day distance truthfully.
  Preserve ordinary scheduling errors, authored fixed gates, computed endpoints
  and retained min/max validation; do not downgrade arbitrary E diagnostics.
- Review Spec04 scheduling/forecast, Spec06 comparison selection, Spec08 warning
  parity, Spec33 Layout ownership and adjacent forecast/text contracts. Publish
  the chosen normative changes and completed architecture review before code.

## Implementation planning boundary

Finalize after design: separate label-eligibility and warning-producer slices,
owned files, neutral tests, publication unit and exact release gates. Expected
owners: projection/label request generation, `forecast_schedule`, warning ledger
and its presentation handoff. No schema/CLI flag or `examples/**` change planned.
Focused tests run in this worktree's `.venv`; CI supplies full pytest,
conformance/wheel, public materializer reproduction and MCP. Inspect one official
public SVG/Scene batch with counts and the actual trial PNG before acceptance.
