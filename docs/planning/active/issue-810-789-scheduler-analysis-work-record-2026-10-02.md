# Work Record - the backward pass inverts lags faithfully (#810) and the analysis is emitted in one order (#789)

**Status:** Proposed. One concise living record for the AGENTS.md sequence (baseline, design plan, design, architecture review,
implementation plan) for two defects in `scheduling/scheduler.py::_analyze_criticality`, taken by one owner in order: #810, then
#789. **Base:** `main` at `c110ad94` (observed 2026-10-02). Every PR is `Refs #810` or `Refs #789`, with no closing keyword.
Owner-level decisions are also recorded on each issue.

## 1. Baseline (verified on `main`)

**#810.** The forward pass places an endpoint at `advance(source endpoint, lag, calendar)` (Spec 04 section 5, 8, 15.1). The
backward pass (`_analyze_criticality`) turns a target's latest endpoint into a source bound with `retreat(target, lag, calendar)`,
which is `advance` of the negated amount. For a working-day amount that is not an inverse: `advance` counts working days
*strictly after* its start, whatever the start is, so every date in a non-working run (and the working day before it) advances to
the same result, while `retreat` of that result returns the *earlier* working day. When the source endpoint is not a working
day of the lag's calendar (the end of a calendar-day span, a point, a source on another calendar) the "latest" source date is
earlier than the source's own earliest date, and `_calendar_distance` raises `TemporalError("Latest placement precedes earliest
placement")`. Nothing catches it: `schedule()` raises for a plan that validates and places correctly.

Minimal reproduction (found on `main`, no derived point involved): a fixed point `2027-05-21` (Friday) feeds a scheduled `2d` span
`s` (placed 05-21 to 05-23, a Sunday end) that feeds a scheduled `5d` span through a `1wd` lag on a six-day calendar. Forward:
Sunday + 1 working day = Monday 05-24. Backward: Monday - 1 working day = Saturday 05-22, earlier than the span's own end.

A second symptom of the same cause does not raise but is wrong: a working-day span whose latest end is a non-working date (a
fixed gate on a Sunday follows a `1wd` span) gets `latest start = retreat(Sunday, 1wd)`, a date from which the forward rule ends
on Monday, after the target, so its float is overstated by one working day.

The property tests of #788 (`tests/unit/chrona/scheduling/test_scheduled_point_properties.py`) stub `_analyze_criticality` because
of this (plan section 11, item 4).

**#789.** `analysis.totalFloat` is built by iterating the set `eligible`, and `ScheduleAnalysis.latest_placements` by iterating
frozen components, so both follow the hash seed. `chrona schedule` prints `totalFloat` as built; the CLI characterization suite
sorts it before comparing (`_canonical_schedule`); MCP `schedule_project` sorts it itself (Spec 66 section 3, with a comment that
names this issue). Spec 57 already says: "Identifiers use the canonical Project object order. `totalFloat` ... includes every
non-rollup scheduled object", and `criticalObjectIds` is already emitted in Project object order, so the CLI contradicts its own
specification. `component_targets` is keyed by `min(component)` in ascending order and is deterministic; `driving_relations` and
`critical` are frozensets that every consumer sorts or tests for membership.

Unverified: the effect on every committed Project (section 5, the sweep). Windows: the change is arithmetic on dates and key order,
nothing path or OS specific.

## 2. Literal acceptance

**#810** (the issue has no checkbox list; its "Needs" paragraph is the acceptance):

- [ ] A minimal reproduction as a failing test.
- [ ] A root-cause analysis (forward and backward passes disagree on lag calendar semantics?).
- [ ] Design-first handling per AGENTS.md.
- [ ] Removal of the stub in the #788 property tests.

**#789:**

- [ ] `chrona schedule` (and every other command whose JSON is deterministic by contract) prints identical bytes under at least
  eight different `PYTHONHASHSEED` values, covered by a test that runs the command in subprocesses with different seeds over the
  starter and HALCYON-1; the characterization suite no longer needs to sort `totalFloat`.

## 3. Decisions (owner-level judgement calls, recorded on the issues)

| # | Decision | Options | Choice and reason | Reverse |
| --- | --- | --- | --- | --- |
| D1 | What the backward pass means | (a) catch the error and report float 0; (b) make the forward pass snap the source to a working day; (c) define the latest source endpoint as the greatest date whose forward `advance` does not exceed the target's latest | (c). (a) hides a wrong number and keeps the overstated float; (b) changes every placement and Spec 04 section 8 ("Zero lag introduces no hidden day adjustment", "Lag arithmetic is separate from target calendar validity"). (c) leaves placements untouched, is the exact dual of the forward rule, and makes float non-negative by construction (Spec 57 already says non-negative). | Restore `retreat` in the three call sites. |
| D2 | Same family, wd span start | fix only the relation hop; also the latest start of a working-day span | Also fix it: the span start is the same inverse problem (greatest working start whose forward end does not exceed the latest end), found by the same property, and it is the only other place the pass inverts `advance`. It changes an analysis value only where a latest end is a non-working date, which the sweep reports. | Keep `retreat` in `_latest_at_target` and `_cap_latest_endpoint`. |
| D3 | Where the inverse lives | scheduler-private; `core/temporal.py` | `core/temporal.py::latest_start_for`, beside `advance` and `retreat` (pure date arithmetic, no scheduler knowledge), tested on its own as a property. | Move it into the scheduler. |
| D4 | Failure of the guard | delete the raise in `_calendar_distance`; keep | Keep it: after D1 it can only fire on a scheduler defect, and a loud failure is better than a negative float. A property over generated plans (section 4.3) now runs the real analysis pass, which is the proof that it no longer fires. | n/a |
| D5 | Order of `totalFloat` | Project object order; sorted by id | Project object order, the order Spec 57 already states and `criticalObjectIds` already uses. MCP keeps its sorted keys (Spec 66 section 3: every mapping is sorted by key), so MCP bytes do not change. | Sort in the CLI instead. |
| D6 | Other hash-ordered mappings | totalFloat only; every mapping built from a set | Every mapping the analysis builds: `totalFloat` and `latest_placements` follow Project object order at the source (one pass at the end of `_analyze_criticality`); `component_targets`, `driving_relations`, `critical` are already deterministic or order-free. A subprocess test over eight seeds checks `schedule` JSON for the starter and HALCYON-1, and `validate`, `render` stderr, `compile` for the starter. | n/a |
| D7 | Spec | none; Spec 57 | Spec 57 states the backward rule (D1), non-negativity, and that every mapping of the analysis is emitted in Project object order; Spec 04 section 20.4's analysis sentence points to it. No schema change. | Revert the text. |

## 4. Design

**4.1 The inverse.** `latest_start_for(target, amount, calendar)` returns the greatest date `s` with
`advance(s, amount, calendar) <= target`. `advance` is non-decreasing in its start, so the greatest such date exists. Start from
`retreat(target, amount, calendar)` (exact for `d`, `w`, `wd` when the start is a working day), step forward while
`advance(s + 1 day) <= target`, step back while `advance(s) > target`. Both loops are bounded by the longest non-working run of
the calendar (or one month clamp), and a `d`-only amount (no calendar) never moves from the `retreat` value, so a plan without
working-day lags is byte-identical by construction.

**4.2 Call sites.** (1) The relation hop in the relaxation loop: `bound = latest_start_for(target_latest, lag, relation_calendar)`.
(2) `_latest_at_target` and (3) `_cap_latest_endpoint`: the latest start of a span with a working-day amount is the greatest
*working* date whose forward end does not exceed the latest end, that is `latest_start_for(end, amount, calendar)` moved back to
the previous working date; a span in calendar days keeps `retreat` (no calendar, exact). Stored latest `end` values are not
changed, so `latest_placements` differ only where a start differs.

**4.3 Properties.** On the helper: for random dates, amounts and calendars, `advance(latest_start_for(advance(s)))` equals
`advance(s)`, the result is at least `s`, and the next day overshoots. On generated acyclic plans with the real analysis pass: no
`TemporalError`, `totalFloat >= 0`, `advance(latest[source], lag) <= latest[target]` for every relation, and a fixed object never
moves. Concrete tests: the reproduction above; the overstated-float case (float 0, not 1); the existing float tests unchanged.

**4.4 #789.** At the end of `_analyze_criticality`, `total_float` and `latest` are rebuilt in Project object order
(`{id: ... for id in objects if id in eligible}`); the intermediate set iteration stays (it is order-free). No adapter sorts a
mapping the scheduler now orders; the CLI characterization helper `_canonical_schedule` is deleted and the golden is recorded as
printed; the MCP sort stays (D5) and its comment is rewritten.

**Failure behavior.** No new diagnostic, no new public key. `chrona schedule` of a plan that raised now succeeds and prints
float; a plan that did not raise prints the same floats except where D2 corrects an overstated one.

**Architecture review.** Core temporal arithmetic gains one pure function; the scheduler is the only caller; no layer, schema,
port or import direction changes (`tools/check_import_direction.py` unaffected); the forward pass and every placement are
untouched, so Scene, View, Layout, derived evidence and the `scheduled-point` rule of #788 are unaffected. Q-SCHED-2 (deadline) is
untouched. Risk: committed Projects with a working-day lag from a non-working source could change float; the sweep decides.

## 5. Implementation plan

| Unit | Content | Gate |
| --- | --- | --- |
| A (this PR) | This record | conformance (docs-only) |
| B (`I810-S1`) | Failing reproduction first (own commit), `latest_start_for`, the three call sites, Spec 57 text, remove the stub and its `mock` import in `test_scheduled_point_properties.py`, new `test_backward_pass_lag_calendars.py` | focused tests, scheduler equivalence sweep (every committed Project, terse fixture and scenario: 52 runs before and after, every difference explained in the PR), conformance, mutation check |
| C (`I789-S1`) | Order at source, subprocess seed test (8 seeds), delete `_canonical_schedule` and re-record the golden if it changes, MCP comment | focused tests, CLI characterization diff reviewed, sweep, mutation check |
| D | Acceptance reviews for #810 and #789 | `tools/check_issue_acceptance_reviews.py`, exact-main three-OS run |

**Must not.** Touch the forward pass or any placement; change `parse_amount`/`advance`/`retreat`; touch #454, #792, #780, #782.

**Sweep.** A script loads every tracked YAML/JSON with `version: timeline/*` and every compilable terse fixture, runs `schedule` and
every Project scenario, and dumps placements, diagnostics and the whole analysis (including key order) before and after.

## 6. Progress

- Unit A merged as #835.
- Unit B (`I810-S1`): implemented as specified (D1 to D4, D7). `core/temporal.py::latest_start_for`; the three call sites; Spec 57
  backward-pass section and a pointer in Spec 04; the stub and its `mock` import removed from `test_scheduled_point_properties.py`
  (a test now asserts the properties run on the real analysis); `test_backward_pass_lag_calendars.py` (the two reproductions,
  failing first in their own commit; two properties of the helper; a 400-plan property over the real pass: no raise, float >= 0,
  `advance(latest source, lag) <= latest target` for every relation). **Sweep** (52 runs: every tracked Project, every Project
  scenario and every compilable terse fixture, placements, diagnostics and the whole analysis, before and after): no placement,
  diagnostic or verdict changes and no run raised before or after. `analysis` differs in 8 Projects, each an instance of the two
  symptoms and each verified by hand: `shipment` in HALCYON-1 (and its baseline snapshot, the cli-characterization copy and the
  terse twins) is a `4wd` span on the engineering calendar whose latest end follows from a `1wd` lag in `range`: the latest end is
  Sunday 2027-09-26 (was Saturday), and the latest start is Monday 2027-09-20; the old Tuesday start would end Monday 09-27 and push
  `campaign` past its own latest start, so its float falls from 5 to 4 (the overstated float); the other baseline-snapshot rows
  (`vibration`, `bus-test`, `integration`) are the same effect one hop upstream. `respin-a1` (Orion, an `8w` calendar-day span with a
  `2wd` lag), `floor` (derived gate) are the true latest end on a non-working date (latest dates move later, float unchanged), and
  `off` in the YAML-hazard fixture is a `2wd` span before a calendar-day span that starts on a Sunday (float 31 to 30). The
  `schedule-halcyon-ok` characterization golden changes in exactly the `shipment` value (5 to 4).
