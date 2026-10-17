# Issue #1634 — opt-in forecast work record

## Baseline and status

Public base: cd4dae681c9fd09f2c26d0dd037fcdac8d97e82d,
merged normally into the feature branch; design PR1642 is merged.
[Owner rule and acceptance](https://github.com/tya5/chrona/issues/1634).
The design plan was published in 783fe50cc; normative design and whole-
architecture review were published in a9c0d3ec6c4b982c1f93249eec6acfcb814632b4;
implementation plan in 00d66e8a5; observed-endpoint correction in ad9dcfb0d before
the corresponding code change. Occurrence coverage was corrected in cab0ae646
before its implementation. F1–F3 are implemented on the feature branch, not
released. Actual trial calculation returns all 25 objects, 6 moved, 22 unfinished,
no fatal errors; the observed dependency miss is reported without changing dates.
Schema equivalence passes all layers for the declared Context/Scene widening.
Focused ingress/projection groups passed (260/314/92); latest completed-label,
Scene, folded/shared-row and tint checks: 110 passed. Skill checks: 51 passed;
the weekly forecast example and validator are complete. Folded packing and final
placement share exact text/icon/chip footprint measurement; the large-chip twin
checks header lanes and required pre-route obstacles. Optional-title policy is
independent. Per-occurrence table coverage and forecast Scene identity are closed.
#1632 code PR #1644 landed as ccf93c0e4 and is merged into this candidate;
its acceptance review PR #1645 is merged; exact-main release acceptance remains pending.
The actual trial PNGs were rendered and viewed at WIP ccc4acf24 and repeated
after integration at cec49ac99 (PNG/Scene byte-identical): target-b
shows 25 forecast/ghost objects and table deltas; technical-print shows 22
selected forecast/ghost objects and independent deltas. Required estimates and
the truthful legend are visible; optional title suppression and preset contrast
findings are separate. These are candidate image checks, not release acceptance.
The no-flag trial matrix is byte-identical to exact main ccf93c0e4 in separate
project venvs: target-b and technical-print, each SVG/Scene/PNG (six pairs).
This proves that matrix, not all public contexts. Post-integration focused tests:
83 forecast/routing, 244 CLI/MCP/closure, and 158 Layout/Scene/geometry-guard tests
passed; all-layer schema equivalence passes. Independent integration audit found
no code or ownership blocker. Next: publish the single feature PR and
inspect its full public artifact comparison, then complete release acceptance.
[Reviewer answers](https://github.com/tya5/chrona/issues/1634#issuecomment-6230794260)
approve retained declared units, finish-only placement with an unobserved-start
finding, and child-envelope precedence with a named group-observation finding.
No owner decision is pending.

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

## Implementation plan

Publish this plan before product changes. Implement the following testable
commits in order; publish the complete opt-in feature as one code PR, not a
partially wired flag or a separate landing for every module. New contract gaps
return to the living design and architecture review before code resumes.

| Slice | Owned files / responsibility | Focused evidence and acceptance |
| --- | --- | --- |
| F1 evaluation | New `usecases/forecast_schedule.py` and neutral typed forecast model; neutral latest-observation selection shared with `presentation/model/projection.py`; existing Core temporal arithmetic and injected Scheduler. | New unit tests cover all literal working-day states/chain; declared d/w/wd retention, fixed-span inference/zero effort, nonworking Actual start, finish-only valid/invalid endpoints, rollup findings, latest/unmatched observations, authored-gate/observed-fixed dependency findings versus unknown/incomplete fatal outcomes, retained explicit bounds, immutability and unavailable analysis. Test the same observed-start overlap shape as trial3 without project names. No presentation import in scheduling/neutral facts. |
| F2 projection and completed geometry | `model/projection.py`, semantic facets/registry, `review/v05_content.py`, Layout member labels/window admission/lane-label preflight, typed completed mark metadata, Scene model/projection and `scene-v0.7` schema. Original facts remain separate from active forecast placement/delta. | Model and integration tests cover Snapshot/no-Snapshot deltas, point/rollup completion, equal-placement ghost, both table source forms and paint, active packing/window/label visibility, required plot text before routes, table/legend/capability refusals, lane-primary inventory and outside-window forecast identity. Existing no-forecast characterization remains unchanged. |
| F3 common ingress | `presentation/contracts/resources.py`, `model/closure.py`, `usecases/draft_render.py`, `usecases/render_review.py`, `app/cli.py`, SDK-free `app/agent_tools.py`, Context v0.17 schema and schema admission fixtures. | CLI render/render-workspace and MCP render_draft (including scoped Snapshot path) reach the same use case. Immutable CLI/MCP read Context only. Absent/false/type errors, exact identity, Actual/asOf requirements and default-preset refusal have tests. Run schema equivalence against ready main and document the precise optional Context and forecast Scene admission deltas. |
| F4 end-to-end and release | Packaged skill's weekly-update section, forecast integration/byte tests and one concise acceptance review. Reviewer owns shared-design YAML; no copied Theme or edited public mirrors. | Render actual trial target-b + packaged technical-print as PNG/Scene; inspect all selected item deltas, required legend/ghost and as-of movement (started bars retain Actual start; fixed targets stay fixed). Compare no-flag artifacts to the ready base in a batch. Official CI supplies public SVG/Scene counts, three-OS full tests/conformance, wheel/smoke and public-materializer reproduction. |

F2/F3 coverage completion: validate actual projected row subjects and folded
occurrences in `render_review.py`; extend `surface_marks.py` header footprint
packing and `surface_member_labels.py` required requests, then project completed
forecast marks/text in Scene. Tests cover folded plot success, missing channel,
hard collision refusal, shared-row subject coverage, and default-off identity.
This correction changes no schema, preset, solver, source selection or layer
ownership; publish it before the corresponding product changes.

Publication boundaries: completed design/review, this implementation plan,
feature commits and code PR, then the literal acceptance/release review. Close
only after its exact review-containing main has the required release evidence.
Run focused tests for each slice, not a duplicate local full suite. Source and
schema changes carry their admission fixtures; bot-owned generated outputs are
never hand-edited. Runtime defaults are implemented, not delegated to schema
annotations. Existing resources need no migration when forecast is absent.
The relation-finding classifier is endpoint-specific: observed start/finish/at
or an authored fixed-point target, never a computed unfinished end or retained
unobserved start. Cover both allowed and rejected endpoints in F1 twins.

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
