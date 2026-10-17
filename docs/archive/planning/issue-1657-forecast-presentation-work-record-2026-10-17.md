# Issue1657 — forecast label ownership and observed-start warnings

Status: issue closed after all four literal acceptance rows met and exact-main release gates passed on [`690f3549ff0b61ee15ed85885ad18aacd7cabf31`](https://github.com/tya5/chrona/commit/690f3549ff0b61ee15ed85885ad18aacd7cabf31). Baseline: main `aabc5e894`, with unchanged product
source from trusted-ready `9f35dd457` after the legend fix.
[Issue1657](https://github.com/tya5/chrona/issues/1657) is closed; issue1397's
implemented slice is preserved separately and publications stay serial.
The [acceptance review](../reviews/issue-1657-forecast-presentation-acceptance-review-2026-10-17.md)
records all four literal rows and the final release evidence.

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

## Selected design and whole-architecture review

Spec06 §8.5 assigns the paired ghost's member-label eligibility to View
projection, independently of temporal paint. A frozen `ReviewItem` eligibility
fact defaults true; one shared row-composition rule disables only Snapshot
companions of a forecasted primary of that object. Every title measurement and
request consumer honours the fact; no Layout project/source-kind exception.
Required forecast deltas and visible ghosts are unchanged.

Spec04 §17.1 defines `W_FORECAST_OBSERVED_START_BEFORE_BOUND`. Classification
requires the effective fixed target to have a supplied observed `start`, not
the diagnostic code alone. Reuse Scheduler evidence; no extra solve or date
mutation. Preserve other reportable fixed targets and fatal validation.
Separate forecast warnings from informational findings in the immutable outcome
and projection; the application sends them through the common warning ledger
(Spec08 §7), not `ForecastInfo`. True FS overlap and other bound misses have
different factual wording. No scalar-expression/predicate feature is added.

Architecture review: Core supplies facts and unchanged Scheduler contracts;
the application derives forecast/diagnostic meaning, View selects occurrence
content, Layout measures/places eligible content, Scene/adapters serialize it.
This matches Spec33/50 ownership and Spec08 warning parity. The deliberate
compatibility changes are removal of duplicate ghost names and the new warning
code/severity for observed-start misses. No resource version, CLI syntax,
source data or ordinary scheduling success contract changes.

## Implementation plan

1. **Label ownership:** `model/projection.py`, member-label measurement/request
   consumers and neutral forecast-render tests. Cover automatic/explicit/lane/
   folded paths, ghost preservation, primary count, ordinary control, mandatory
   delta and unchanged no-forecast output.
2. **Warning classification/transport:** `core/forecast.py`,
   `usecases/forecast_schedule.py`, projection/application handoff and
   `warning_ledger.py`. Cover observed/forecast predecessor finishes, completed
   and unfinished observed targets, SS/positive/negative lag, retained bounds,
   unobserved endpoints, fixed gates, warning severity and Scene/CLI identity.
3. **One implementation PR:** separately reviewable commits, concise literal
   acceptance review, one official public SVG/Scene snapshot count batch and
   actual trial technical-print PNG. No generated edits or `examples/**` changes.
Focused tests run in this worktree's `.venv`; CI supplies full pytest,
conformance/wheel, public materializer reproduction and MCP. Inspect one official
public SVG/Scene batch with counts and the actual trial PNG before acceptance.

## Current verification

The combined scheduling, warning transport, render/occurrence, projection and
lane-label batch passes118 tests. An additional end-to-end render test proves
one-day observed overlap warning severity and Scene/CLI diagnostic identity.
The exact immutable trial3 technical-print PNG was rendered and viewed: one
member name per object, visible baseline ghosts and required deltas retained.
Its wireframes→visual-design warning states observed November9 start before
observed November10 finish, overlapDays=1, severity warning, without the former
E_FIXED_TARGET_VIOLATION. Neither source files nor examples were edited.
PR1662's official snapshot39037416367 on reviewed head
`b7799320b9c0b91c4d7ca4399f1613971304c38e` confirms all50 SVG+50 Scene files
byte-identical, same109 paths; only diagnostic inventory changes
(304211→304383 bytes). Squash commit
`5080e1c351c1a041054252c7e8fc394b5c1f5c3d` has the same tree. Exact-main
release run [39038812877](https://github.com/tya5/chrona/actions/runs/39038812877)
passed the three-OS full matrix, public-materializer reproduction and MCP floor.
