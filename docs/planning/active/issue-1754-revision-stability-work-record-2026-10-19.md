# Revision stability — issue 1754

## Published baseline and scope

Design planning; no implementation approved yet. Source: [issue 1754](https://github.com/tya5/chrona/issues/1754), including its later comments, on ready main `6c3b4e4e2d4064e924a8b9703c3f31ab7a62bc39`.
Trial evidence is reference-only: [`reviewer/trial-8-inputs@bf3940dbe9af487ac6cace5458554762594f3477`](https://github.com/tya5/chrona/tree/bf3940dbe9af487ac6cace5458554762594f3477/trial-8).

Published facts: core relation identities include the declaration index;
Layout consumes previous-Scene hints only under first-fit; Spec 50 explicitly
excludes best and makes the as-of rule obstruct member names; Specs 08/46
include the cone in completed contrast grounds. These contracts must change
before code. Trial measurements are reported evidence, not yet independently
reproduced on the implementation. Duplicate declared-ID handling, best-mode
hint preference and the Theme ground opt-in remain design decisions.

Dev A owns this item. Dev B owns baseline/forecast 1755 and customisation
1756. Coordinate shared-file changes before implementation; do not alter trial
inputs or preset YAML to satisfy a general rule. Completed 1734 geometry reuse
and its safety/accounting rules remain the routing baseline.

## Literal issue rules

1. A relation with a declared, unique `id` is identified by that id alone. Without one, it is identified by its endpoints and type, with a declaration-order suffix only to separate exact duplicates.
2. Previous-Scene hints apply under every search policy: as the first candidate for `best` as well as for `first-fit`, still revalidated. Where a policy cannot use them, emit an `I_` diagnostic saying so.
3. A route whose endpoints and obstacles near it are unchanged keeps its corridor when one still validates (hint-first). Prefer a detour over crossing a mark before accepting a through-mark route.
4. The as-of line is not a label obstacle that suppresses a member label: labels may cross it, using the existing halo/chip treatment.
5. Contrast observations over a moving decoration (the as-of cone) are judged against the mark's own ground, not the cone, unless the Theme declares otherwise.

## Literal acceptance and required evidence

| # | Literal acceptance criterion | Evidence to produce |
| ---: | --- | --- |
| 1 | Synthetic: removing one relation and appending another keeps every other relation's primitive id; hints are accepted for all unchanged relations. | Canonical identity, scheduler/Model/Scene and previous-Scene synthetic tests, including anonymous/duplicate relations. |
| 2 | target-b with `--previous-scene` uses the hints (receipts show accepted hints), or reports why not. | Real render and per-instance/summary receipts under best, plus unsupported-mode diagnostic tests. |
| 3 | A synthetic slip that does not touch a relation's endpoints keeps that relation's route; no new through-mark crossing appears where a detour exists. | Completed-route geometry before/after, current validator results and an obstructed-route negative twin. |
| 4 | Re-running trial 8 with hints: the changed-primitive count of unchanged objects falls, and the table is posted on the issue. executive-light labels of unchanged tasks do not toggle with the as-of line. | Batch all five weeks/three designs, compare unhinted and hinted revisions on the same candidate, post table and inspect rendered label output. |

## Design plan and architecture review questions

Use cases are weekly redraw, inserted/removed relations, unchanged corridors
beside unrelated edits, and moving as-of decoration. Preserve intent and
source identity in core; normalize relation facts in Model; keep hint recovery,
geometry, obstruction and route validation in Layout. Scene observes completed
paint/grounds; adapters serialize without inferring placement or policy.

Review before selecting contracts:

- Define collision-free identity namespaces and duplicate occurrences, including
  duplicate declared IDs, endpoint/type normalization and public-ID migration.
  Audit scheduler critical/driving relations, lane projection and Scene matching.
- Specify hint-first acceptance under best versus ranking only fresh candidates,
  current full safety/quality validation, invalidation, receipts and budgets.
  Separate primary marks from other obstacles; never infer safety from trial data.
- Remove only the moving as-of line from member-name obstruction; retain
  deadline/other-rule contracts, route/annotation safety and existing text treatment.
- Specify precisely which contrast observations use the mark's own ground,
  how an explicit Theme declaration requests cone compositing, and transport
  through schema/Model/completed Scene without adapter-specific behavior.
- Check Specs 06/07/08/46/50/56, relevant ADRs and adjacent 1755/1756 work;
  identify intended output/diagnostic incompatibilities and old-Scene hint misses.

## Publication and implementation planning gates

1. Publish this plan before making decisions in code.
2. Complete the selected design and whole-architecture review here; update the
   living specifications. Publish before finalising implementation planning.
3. Publish implementation slices with exact owned files, focused tests,
   schema/resource migrations and affected materializer/generated-evidence gates.
   Candidate boundaries are stable identity, all-policy hint reuse, moving
   decoration handling, then integrated trial acceptance; revise after design.
4. Implement approved slices only. Run focused synthetic tests locally in this
   worktree's venv. Batch public SVG/Scene comparisons and trial renders;
   use CI for full three-OS pytest/conformance/wheel/materializer evidence.
5. Publish one literal acceptance review and release on exact main containing
   it. Close only after every row and required release job succeeds.

No product implementation or trial reproduction is complete at this stage.
