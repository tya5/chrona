# Issue #1634 — forecast architecture review

Status: design and implementation plan published; the semantic-identity correction
below was published in e0c26e3d4 before implementation611e8e850. PR1646 is merged;
issue1634 is closed after [release39019665585](https://github.com/tya5/chrona/actions/runs/39019665585)
passed on exact ready main `cf121865552017a2a97a13cd094bde641686c261`.
[Archived work record](../planning/issue-1634-forecast-work-record-2026-10-17.md).

| Boundary | Consistency check |
| --- | --- |
| Core / Actual | Spec04 §17.1 is explicit derived evaluation. Original Project, placements, Actual endpoints/progress and Snapshot stay immutable. Declared amount units are retained; only fixed spans infer effort. Nonworking starts retain their observed date; finish-only and conflicting rollup observations produce findings without fabricating Actual facts. |
| Scheduler / application | Spec09 gives orchestration to the Forecast Coordinator, not a second solver or the ordinary engine. Complete authored fixed-point/observed-fixed endpoint findings are reported, not repaired. Other failures and explicit bounds remain fatal; classification uses the source/observation and effective endpoint, not only the diagnostic code. Ordinary success and unavailable analysis are not rewritten. |
| Observation selection | One neutral latest selector preserves ordinary positive-sequence/unmatched behavior. Scheduling never imports presentation or selects observations through a View. |
| View / comparison | Spec06 §8.5 keeps original facts and a separate forecast fact. Text and variance paint select the same active comparison. A supplied Snapshot stays visible even at equal placement: an explicit forecast-only override of omitted/changed-only ghost policy, not a change to ordinary defaults. Explicit rows, point endpoints and missing baselines are explicit. |
| View / geometry | Source selection/order and source-date bindings retain their meaning. Active forecast intervals drive geometry/packing, label-window admission and lane-label preflight; derived windows include forecast/ghost endpoints. Explicit windows remain authoritative. |
| Layout / Scene / adapters | Spec33's existing required-text path reserves independent deltas before routes. Required text remains hard in staged routing. No new placement algorithm, extra rehearsal, adapter font discovery or Scene date arithmetic. Spec08 closes forecast purpose/facet with planned paint, primary lane inventories and forecast/planned window-absence evidence; registry/model/schema must widen together. |
| Profiles / resources | Spec50's legend-slot authority stays intact. An incapable View/Profile refuses the mode rather than inventing a footer, editing examples or hiding selected work. Optional titles remain optional; required deltas do not inherit title suppression. |
| Occurrence coverage | A table cell covers its declared row subject, not every primary item in a shared explicit row. Folded points have no table cells and need the declared plot delta channel. Layout reserves each full header delta in packing and before routes; Scene projects its forecast mark/text identity. Missing declaration is a capability error, spatial failure is required-text refusal. No implicit destination, extra table row, unfolding or selection change. |
| Context / CLI / MCP | Spec13 has one optional boolean with runtime omission behavior; immutable Context identity remains exact. Spec08 routes Draft CLI/MCP through the same closure, including workspace-scoped MCP Snapshot input. No second immutable-render override. |
| Schema / compatibility | The optional control preserves prior valid resources and default output. Spec56 equivalence/admission evidence is required at implementation; no version is bumped merely for widening. Forecast diagnostics apply only when explicitly requested. |
| Adjacent source facts | Source-plan deadline verdicts, periods, planned annotation anchors, observed counts and figures retain their meaning. Original criticality cannot masquerade as unavailable forecast analysis. |

Three independent read-only reviews covered scheduler states, presentation and
whole-architecture closure. Resolved findings: retain declared units per the
reviewer answer; finish-only/rollup findings are nonfatal; narrow the fixed-target
classification; register Scene forecast/lane/window identities; rebase label admission
to active geometry; name technical-print as the public generic preset; and make
Snapshot ghost retention an explicit forecast-only override. No unresolved design
gate remains. Trial3's wireframes Actual ends Nov10 while visual-design Actual
starts Nov9: this established the general observed-fixed finding policy before
changing that code. Actual truth, forecast propagation and ordinary scheduling
are separate; neither source dates nor relations are silently edited. Synthetic
twins must cover completed spans, observed starts and observed points, alongside
fatal unknown-target/incomplete outcomes. Local documentation guards: 28 passed;
`git diff --check` clean.

Semantic-identity correction reviewed against Spec06 fact separation, Spec08
identity and the global registry uniqueness invariant: forecast plot deltas need
their own purpose, not aliases of ordinary delta bindings. Existing paint roles
remain reusable. Layout/Scene/adapter ownership, geometry, table-cell semantics,
schema admission and absent-flag output do not change. Publish this correction
before changing registry bindings; retain the uniqueness guard unchanged.

Release is separate: every literal criterion, original-trial PNG evidence,
public artifact counts and exact review-containing three-OS CI.
