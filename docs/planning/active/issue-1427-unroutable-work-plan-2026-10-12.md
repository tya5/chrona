# Unroutable dependency resolution (#1427)

Design published in PR1441; implementation is underway on the issue WIP. Public base:
READY `872318db36032cf135f71c605d48d80c36c798f9`, full release
[38257798618](https://github.com/tya5/chrona/actions/runs/38257798618) passed.
Authority: [issue](https://github.com/tya5/chrona/issues/1427) and
[reviewer decisions](https://github.com/tya5/chrona/issues/1427#issuecomment-6125006829).
Current [Status](https://github.com/tya5/chrona/issues/1427#issuecomment-6114823479).

Current slice: critical facts/order and typed mode admission are staged.
Search, port admission, side-entry alternatives, reduction, primary-mark and
corner validation now use the same stage domain. Finite fixed overlap is
connected and never searches; paired stub fragments and mandatory ASCII
terminal labels are connected through completed Layout placements. Scene
retains its paired-reference invariant and performs projection only.
Synthetic collision-domain tests prove Scene/SVG recovery and quality-limit
fallback; search receipts remain separate from completed side-entry choices.
Typed completion diagnostics now retain critical/stage identity and per-surface
counts. Only the selected placement trial contributes recovery facts; executed
search-budget facts still include discarded trials. Paired fragments count as
one relation. The shared warning mapper serves CLI and MCP without recounting.
Completed halo geometry now projects below its recovery line and existing text;
normal/suppressed paths remain untouched. Theme owns surface-ground paint and
validated width; decoration contrast remains enforced. Visible-obstacle release
evidence, public byte controls and the final default flip remain incomplete.
This is not release acceptance. The staged default stays suppress until the
atomic protection/recovery gate below is satisfied.

Latest focused gate: 196 tests pass, including real Scene/SVG halo ordering,
Theme width controls and decoration contrast. Conformance: 32 checks pass;
three derived reports are stale (contrast, diagnostic inventory and presentation
coverage). Regenerate these in the disposable release snapshot, not as
PR-authored report edits. A public recovery halo witness is still needed.
Legacy View supersession is now typed and projected once per completed surface;
an agreeing suppress or omitted View declaration remains silent. Explicit Layout
suppress also overrides legacy visible-overflow. Focused controls: 113 pass.
The staged suppress public materializer batch passes full Scene/SVG byte identity
for all 46 contexts, including critical-order integration (zero route deltas).
Evidence: `python -m tools.routing_performance_evidence --output-dir <empty-dir>
--jobs 4`; the batch JSON and all actual serialized outputs are retained for PR
evidence. This does not prove the default-relax acceptance or final protection.
Isolated relax-default candidate (only engine/model defaults changed): all46
materializers complete; zero route additions/removals/geometry changes, zero
spatial suppressions and zero recovery stages. The45 changed Scene/SVG pairs
carry policy/provenance/migration diagnostics, not routing changes. Actual launch
v1/v2 `spec-build` Scene/SVG regression passes under both staged suppress and
candidate relax. Reviewer coordination for target protection and an enabled
public halo witness is tracked in
[comment6127633845](https://github.com/tya5/chrona/issues/1427#issuecomment-6127633845).
The four-mode blocked-plan test now supplies one completed Layout mark spanning
the plot before shared obstacle registration. That exact mark is projected and
serialized visibly, unlike the earlier collision-index-only constraint fixture.
It proves suppress versus marks-stage recovery, overlap and paired-stub output;
stub fragments still count once. It is intentionally a completed Layout input
fixture, not a claim that normal lane packing creates overlap, and not a public
decoration witness.

## Literal acceptance

| Criterion | Required evidence |
| --- | --- |
| Under `suppress`, every example is byte-identical. The reviewer declares `suppress` on the five approved design targets before the default flips, in the same coordination as #1426's `search: best`. | All 46 current-main full Scene/SVG controls; reviewer protection merged before default flip. Separate truthful resource-provenance changes from geometry. |
| Under the default `relax`, the trial's v2 launch plan draws `spec-build`, and every relation of every example slide is drawn. Count the stage used per slide in the PR. | Actual trial plus all 46 serialized materializers; instance identities and stage counts, not warning absence alone. |
| A test per mode on a synthetic plan where one relation is fully blocked. | Real Layout/completed Scene/SVG for all four modes, with failure/budget controls. |
| Halo paint order: the line lies below text in the Scene. The halo is a decoration under the contrast policy. | Completed paint relations and serialized adapter order; decoration classification, no mark-floor waiver. |
| Do not edit `examples/**`. | Exact PR diff; permanent target declarations are reviewer-owned. |

## Design and architecture review

Use cases: ordinary readers retain links despite obstructed routes; authors may
choose unsafe overlap, paired terminal stubs, or legacy suppression. See
[Spec50 §3.3](../../specification/50-constraint-driven-gantt-surface-quality.md#33-relations)
for the single normative contract. No project-size or corpus-specific branch.

Core owns zero-float dependency facts, not geometry. Presentation closes those
facts and endpoint titles. Layout owns stage attempts, endpoints, host egress,
routes, stub/label measurement and completed halo geometry. Theme supplies halo
paint. Scene projects completed primitives and typed evidence; adapters serialize.
Reuse existing path, text, terminal and obstacle machinery. Do not duplicate the
normal selector inside each mode or put fallback routing in Scene.

Consistency: Specs03/06 preserve scheduling/selection; Specs08/33 preserve
completed placement and projection; Spec46 retains decoration contrast;
Specs50/66 retain fresh per-instance/pass budgets and window endpoint absence;
Spec56 now records the explicitly authorized #1430/#1427 exception: additive
shared vocabulary in the same schema, with an incompatible runtime default,
documented migration and reviewer protection. This is not a blanket version
waiver or a claim that omission preserves old behavior.
Critical-first facts/order from the approved #1300 WIP are a prerequisite;
integrate those independent slices with current canonical IDs/progress. Do not
include previous-Scene hints or claim protected feasibility. Unsafe modes
supersede the older critical safety disposition; explicit suppress does not.

Migration review question: an agreeing View/ Layout suppress value has no
superseded meaning, so preserve its bytes without a migration diagnostic. Emit
one info only when Layout changes the legacy value's meaning. All 42 corpus
Views with explicit relation overflow currently declare suppress. This
interpretation reconciles the migration notice with the literal byte control;
review it before implementation is finalized.

## Implementation plan

Halo completion: Theme supplies surface-ground ink and declared/default width;
Layout closes a separate immutable centreline/curve/clip/order placement.
Scene emits its decoration path without markers or graph references. Specs08/33
retain projection-only Scene, Spec46 retains decoration contrast and witness
coverage. Width/paint validation remains hard; no renderer-side fallback.
Publish this Spec50 clarification before halo implementation.

Stub completion clarification: admitted endpoints retain independent fragments
and mandatory terminal text under visible overflow, including plot-edge cases.
Window endpoint absence still precedes routing. Spec50 owns this selected rule;
Specs08/33 retain completed path/text projection and canvas ownership, while
Spec66's temporal selection remains unchanged. Layout retains partial endpoint
ownership, but Scene fragments omit graph references to preserve its existing
both-or-neither invariant and avoid describing a full connected edge. Publish this
clarification before connecting stub geometry/text; no adapter inference or
new author syntax is needed.
Terminal direction tokens are ASCII `->`: actual stub wiring exposed a missing
U+2192 glyph in the bundled font stack. The ordinary font contract stays hard;
do not add a renderer substitute, bypass glyph validation or silently change
the author's font stack. Endpoint titles still use normal text measurement.

One implementation PR after this design publication; independently tested commits.

| Slice | Owners/files | Gate |
| --- | --- | --- |
| A — contracts and critical order | Core-derived critical facts; `surface_content`, Layout `model`/`engine`, shared vocabulary and Layout schema, typed resolution evidence | Existing #1300 priority/progress/canonical identity tests; schema S0, absent/invalid/inherited mode, suppress control. |
| B — staged Layout resolution | Extract normal attempt ownership from `surface_routes`; mode coordinator, obstacle filtering, endpoint-host preservation, per-end stub labels | Actual blocked fixtures; each stage calls declared search; independent budgets, exact rescue, finite fallback, one resolved instance counted once. |
| C — completed paint and projection | Layout placement/completion, Theme halo fallback, semantic registry, Scene projection, CLI/MCP info mapping | Below-text halo/path order in real SVG; no Scene measurement/routing; critical/stage facts and count correspondence. |
| D — acceptance/publication | Synthetic controls, actual launch pair, batched public materializer evidence and concise literal review | All 46 suppress byte controls, default routes/stage/delta table, reviewer-protected five, focused tests, current-base PR CI and exact-main three-OS release. |

Stage the schema/mode implementation with legacy suppress on the PR branch so
the reviewer can supply protection commits. Include those reviewer-owned
declarations before the final default flip in the same atomic release; no
intermediate main state exposes new defaults without target protection.
Measure critical-order predecessor effects independently. If that approved
integration changes legacy artifacts, review/publish it before fixing the
#1427 suppress reference base; do not conceal it with a mode-specific ordering
compatibility branch or claim byte identity against a different base.

Reviewer protection precedes the default flip. If a contract gap appears, update
this record/specification, repeat whole-architecture review and publish before
resuming that slice. Keep local optional polish separate; do not expand scope.
