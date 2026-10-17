# Issue #1634 — opt-in forecast work record

## Baseline and design plan

Published base: ready `fa262ebab648229138eb34c33bf6a821f6450e96`.
[Owner rule and acceptance](https://github.com/tya5/chrona/issues/1634).
Design preparation only; finish the active1610/1583 and1612 landing first.
No forecast code or final implementation plan is approved by this record.

Published facts: Spec04 §17 and Spec06 §§4.2/8.2 keep Actuals observational.
`scheduling/scheduler.py` already owns calendar-aware dependencies, rollups and
fixed-target diagnostics; `core/temporal.py` owns working-day arithmetic.
`usecases/render_review.py` schedules primary and Snapshot Projects independently;
`presentation/model/projection.py` combines placements, Actual facts and deltas.
Render Context v0.17 has no forecast control. These existing seams are the
starting point, not proof that forecast requirements already work.

Use case: explicitly ask for a current estimate from observed Actuals while
retaining the authored plan and optional baseline. Default rendering must not
change. Design a separate derived schedule, not post-Layout geometry shifts or
mutations to the Project/Snapshot. Reuse existing calendar/dependency rules;
keep forecast intent and estimated delta facts out of Scene/adapters.

Baseline architecture constraints (also checked at merged main340b9e708):
`_place_scheduled` treats anchors as authoritative; an as-of start floor alone
cannot move every existing span, nor extend an active anchored end. Forecast
therefore needs an explicit effective-schedule normalization, not hidden source
Project rewrites or a second ad-hoc dependency solver. `working_days_in` counts
`[start,end)`, whereas `advance(..., Nwd)` counts work-date transitions after its
start; actual non-working starts and zero-work fixed spans need deliberate rules.
Ordinary `_project_review` rejects any scheduler diagnostic, including a missed
fixed target. Preserve that behavior: a separate typed forecast outcome must
distinguish complete placements plus reported fixed-target findings from fatal
or incomplete schedules. A broad diagnostic-ignore switch is not acceptable.

Design questions to resolve before implementation:

- Keep progress observed-only (recommended); no percent-to-duration inference.
- Define the explicit cutoff source and failure for missing Actual/asOf; latest
  observation selection, missing endpoints, point observations and completed
  facts conflicting with dependency bounds must be unambiguous.
- Define planned-duration derivation for fixed and scheduled spans, effective
  calendars, movable bounds versus preserved fixed points, and rollup treatment.
- Distinguish estimated forecast deltas from ordinary observed `finishDelta`;
  preserve Snapshot ghosts and use the original plan when no Snapshot exists.
- Coordinate forecast legend/style with reviewer-owned shared-design YAML.
- Decide saving a forecast as a Snapshot; recommend no implicit save or source
  rewrite, with any explicit export requiring its own identity contract.

## Selected architecture (design not complete)

- One effective control: optional `RenderContext.body.forecast`, runtime false
  when absent. Draft CLI/MCP normalize into that control and omit false; do not
  add a competing flag to immutable `RenderRequest`. Require Actual Set `asOf`;
  no wall-clock, viewport or fabricated Actual-finish fallback.
- A neutral latest-observation selector can serve ordinary projection and
  forecast input without scheduling importing presentation contracts. Preserve
  unmatched reporting and normal-path selection behavior.
- Forecast scheduling reuses the injected scheduler on explicit, non-mutating
  effective inputs (the existing Scenario resolver is an adjacent pattern).
  Its typed outcome separates fatal errors from complete placements carrying
  known fixed-target findings; ordinary `ScheduleOutcome.ok` is unchanged.
- Keep original `ReviewItem.planned`, Actuals and observed `finish_delta` intact.
  Carry one optional forecast fact with placement, comparison baseline and
  estimated status; select its mark instead of the primary planned mark.
  Snapshot ghosts remain independent. No parallel full projection or synthetic
  Actual Set. Layout owns geometry and formatted estimate text; Scene/adapters
  receive completed primitives only.

The [two concrete policy questions](https://github.com/tya5/chrona/issues/1634#issuecomment-6229844456)
cover zero-work/non-working duration and incomplete/composite Actuals. Their
disposition, display/legend contract and whole-architecture review still precede
normative design completion and the final implementation plan. No product code.

### Scheduler feasibility trace

The existing scheduler can consume a derived Project without a new port or a
second dependency solver. The following normalization remains a design candidate,
subject to the duration and incomplete-observation decisions above:

| Source state | Effective scheduling input |
| --- | --- |
| Finished span, both Actual endpoints known | Fixed span at those exact observed endpoints; never move a fact to satisfy a dependency. |
| Started span | Fixed observed start and retained-duration end, extended to at least explicit `asOf`. Incoming contradictions are findings, not permission to rewrite the observed start. |
| Unstarted span | Scheduled amount with start floor at least the original planned start and `asOf`; replace authored date anchors only in this explicit derived input, retaining applicable bounds/calendar/dependencies. |
| Scheduled point | Reuse the existing scheduled-point dependency rule and cutoff floor; an observed `at` supplies its completed fact. |
| Fixed point / rollup | Preserve the fixed target; derive rollup envelopes from forecast children rather than adding a second group scheduler. |

`_validate_fixed_targets` already returns placements with explicit endpoint
findings. The forecast wrapper must whitelist only that known finding class
and require a complete, kind-valid placement set; cycles, absent endpoints,
invalid amounts/calendars and contradictory movable bounds remain fatal.
Do not call an unsuccessful ordinary outcome successful, or reuse absent
criticality analysis as if forecast float/critical-path facts were computed.
The wrapper's source mappings must preserve original object/relation pointers
in diagnostics; the derived Project is neither persisted nor exposed as a new
Snapshot. These are scheduling/application contracts, not Layout conditions.

## Design and implementation publication order

1. Complete normative Spec04/06 and CLI/Context/MCP contracts, diagnostics,
   provenance and default-path preservation. Review against Actual/Snapshot,
   scheduler, View/Theme/Layout/Scene and schema ownership. Apply Spec56 §3.2:
   do not introduce a version merely for an optional additive control.
2. After that design is published, finalize independently reviewable slices:
   pure forecast scheduling; projection/estimated deltas; CLI/Context/MCP;
   presentation adoption, skill and release evidence. Name concrete files,
   migrations, focused tests and public output boundaries in this record.
3. Implement only those approved slices; return to design for contract gaps.
   Focused local tests, schema equivalence when applicable, batch public output
   review, and exact-head CI/review-containing three-OS release are required.

## Literal issue acceptance (all pending)

- [ ] Design and specification published before code: Spec 04 and 06 sections for the forecast layer, and the CLI/Context field.
- [ ] Synthetic tests:
  - finished, started-late, started-overrunning and not-started items with a successor chain, on a working-day calendar;
  - a `fixed-point` gate missed by a forecast successor is diagnosed.
- [ ] Without `--forecast`, output is byte-identical to main.
- [ ] Trial 3's plan with its `actual.yaml` and `baseline.yaml`, rendered with `--forecast` in target-b and one generic preset: unfinished items carry an estimated Δ finish against the baseline, and no unfinished bar sits before as-of. Viewed as PNG.
- [ ] The skill's "Update the plan after a week of work" section mentions `--forecast`.

Exact trial inputs are not yet linked in the issue. Obtain them for the literal
visual criterion; synthetic fixtures cannot substitute for that evidence.
