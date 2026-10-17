# Issue #1634 — opt-in forecast work record

## Baseline and status

Public base: 41e6c83a9f742af6e7a46209c4cec8f4bca91f0f (trusted-ready).
[Owner rule and acceptance](https://github.com/tya5/chrona/issues/1634).
The design plan was published in 783fe50cc; the normative design and whole-
architecture review are complete for publication. No forecast product code or final implementation plan is
published yet. [Reviewer answers](https://github.com/tya5/chrona/issues/1634#issuecomment-6230794260)
approve retained declared units, finish-only placement with an unobserved-start
finding, and child-envelope precedence with a named group-observation finding.
No further reviewer gate precedes normative publication.

## Selected design and authority

| Contract | Current authority |
| --- | --- |
| States, effort, calendars, fixed targets and failures | [Spec04 §17.1](../../specification/04-scheduling-model.md#171-explicit-forecast-1634-designed-implementation-pending) |
| Facts, estimated deltas, ghosts and required presentation | [Spec06 §8.5](../../specification/06-view-model.md#85-explicit-forecast-presentation-1634-designed-implementation-pending) |
| One Context control and omission/identity | [Spec13 §5.3.1](../../specification/13-presentation-format.md#531-explicit-forecast-control-1634-designed-implementation-pending) |
| CLI/MCP ingress | [Spec08](../../specification/08-scene-and-rendering.md#explicit-forecast-ingress-1634-designed-implementation-pending) |
| Component boundary and required text | [Spec09](../../specification/09-application-architecture.md#5-read-evaluation-flow), [Spec33](../../specification/33-intent-oriented-layout.md#9-diagnostics) |
| Whole-architecture review | [Current review](../../reviews/current/issue-1634-forecast-architecture-review-2026-10-17.md) |

The application normalizes a non-persistent effective Project and reuses its
injected Scheduler; ordinary ScheduleOutcome.ok is unchanged. Declared amounts
retain their unit; fixed spans infer effort from the original resolved interval.
Missing completed-span starts and contradictory group observations are findings,
not fabricated Actual facts or a reason to freeze the forecast. Zero inferred
unfinished effort refuses forecasting without inventing a minimum.
Progress remains observed-only; no implicit forecast-to-Snapshot save is added.

Projection retains original planned/Actual/observed variance and adds one typed
forecast fact. A central display selection serves geometry/packing, forecast
comparison text and variance paint; source-plan queries remain source-plan
queries. No duplicate full projection, second solver or Scene/adapter policy.

Forecast requires a declared legend slot and per-item delta channel. Reuse
planned paint and existing required-text/atomic-table mechanisms rather than
inventing slots or suppressing estimates. Initial image acceptance targets are
target-b and technical-print; the latter needs independent required plot deltas,
not a suppressible combined title. Other Views may declare the same
capabilities; an unsupported View fails with a concrete capability diagnostic.
This is a forecast-only contract, not a default preset or example rewrite.
The shipped default currently has no delta channel: test and document its typed
refusal with guidance to use a forecast-capable preset; do not silently alter
its declared View or ordinary output.

## Design review and implementation publication order

1. Review the normative design against Core amount/authority rules, Actual
   selection, Snapshot/scenario identity, Context/schema evolution, View
   selection/explicit rows, lane packing, Layout text/route ownership and
   source-plan deadline/annotation/figure consumers. Publish the completed
   design/review before treating implementation planning as final.
2. Finalize independently verifiable slices in this record: forecast evaluation
   and neutral observation selection; projection/geometry/required comparison;
   CLI/Context/MCP and schema admission; skill and release evidence. Name exact
   owned files, migrations, tests and publication units after design review.
3. Implement only the published plan. New contract gaps return to design before
   code. Run focused local tests; use CI for full three-OS release evidence.

Planned ownership: Core temporal/neutral observations retain date and selection
primitives; usecases/forecast_schedule.py coordinates the Scheduler;
render_review.py transports typed results/findings. Projection/semantic facets
select data; Layout completes marks, tracks, ports, required text and routes.
Context/Draft/SDK-free agent tools normalize ingress; Scene/adapters serialize.
Schema additions use the existing version with tested omission, an exact L1
admission delta and schema-equivalence evidence. No generated mirrors are edited.

Evidence must include working-calendar state twins, missed fixed targets,
incomplete/zero-effort/rollup diagnostics, latest/unmatched observation identity,
source immutability, absent-flag byte identity, changed forecast packing and
window and label admission, Snapshot-equal-plan ghost visibility, required delta/legend refusal,
and CLI/MCP normalization parity. Review actual PNGs and official public
SVG/Scene counts as a batch; tests alone do not establish acceptance.

## Literal issue acceptance (all pending)

- [ ] Design and specification published before code: Spec 04 and 06 sections for the forecast layer, and the CLI/Context field.
- [ ] Synthetic tests:
  - finished, started-late, started-overrunning and not-started items with a successor chain, on a working-day calendar;
  - a `fixed-point` gate missed by a forecast successor is diagnosed.
- [ ] Without `--forecast`, output is byte-identical to main.
- [ ] Trial 3's plan with its `actual.yaml` and `baseline.yaml`, rendered with `--forecast` in target-b and one generic preset: unfinished items carry an estimated Δ finish against the baseline, and no unfinished bar sits before as-of. Viewed as PNG.
- [ ] The skill's "Update the plan after a week of work" section mentions `--forecast`.

Exact trial inputs and commands are public at
[dbbce45e/trial3](https://github.com/tya5/chrona/tree/dbbce45e60392b7b0be788f841fe2673f4830944/trial3).
Read this reference branch without merging it. The published README names
technical-print alongside target-b as a trial preset; the generic acceptance
render uses the shipped technical-print preset, not a target-specific fixture.
A synthetic fixture is never presented as the actual trial.
