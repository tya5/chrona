# Unroutable dependency resolution (#1427)

Design publication; product implementation has not started. Public base:
READY `d1f502c1ebba398686eeaa7866e3a1ef3ef6d7bb`, full release
[38246924810](https://github.com/tya5/chrona/actions/runs/38246924810) passed.
Authority: [issue](https://github.com/tya5/chrona/issues/1427) and
[reviewer decisions](https://github.com/tya5/chrona/issues/1427#issuecomment-6125006829).
Current [Status](https://github.com/tya5/chrona/issues/1427#issuecomment-6114823479).

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
