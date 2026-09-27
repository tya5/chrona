# Implementation Plan — Missing Actual Due-State (#476)

**Approved design:** [semantic contract](../../design/issue-476-missing-actual-due-state-design-2026-09-26.md), [whole-architecture review](../../reviews/current/issue-476-missing-actual-due-state-architecture-review-2026-09-26.md), and amended Specifications 06/08/25/39/46 at `dfce9db0`. **Fixture caveat:** [plan amendment](issue-476-missing-actual-due-state-design-plan-amendment-2026-09-26.md); the published HALCYON TVAC observation must not be removed.

## Literal acceptance ledger

1. On HALCYON-1 at as-of 2027-08-20, items planned to finish after
   2027-08-20 carry no missing-actual mark.
2. Items due on or before as-of with no observation still carry it. `tvac`
   (planned finish 08-20, no observation) is the boundary case, and a test
   covers it. The public input has an observation; test with an explicit
   copy that removes only that entry, and await owner clarification before
   closing the issue.
3. The `missingActual` table cell follows the same rule.

## I476-1 — Atomic semantic and geometry migration

Affected owners: `src/chrona/presentation/model/projection.py` adds one closed
typed observation state and derives it from selected Actual + explicit as-of;
`model/surface_content.py` maps that state to the tri-state table source;
`review/v05_content.py` uses it for cell semantic and summary count;
`layout/presentation.py` reserves only actual or due-unobserved geometry;
`layout/surface_composer.py` emits the missing mark only for due-unobserved.
Scene and renderers must remain projection/serialization only. Remove every
parallel `not bool(item.actual)` missing-Actual decision in these consumers.

Focused tests: projection span/point due equality and future, present
incomplete observation, no as-of, explicit/shared/snapshot rows; table
true/false/unavailable and semantic role; summary count and unavailable
metric; Layout track/mark placement; CLI/Scene/SVG HALCYON at 2027-08-20,
including a test-only Actual copy with TVAC observation removed. Assert
future `shipment`, `campaign`, `frr`, `launch`, `rehearsals`, `leop`,
`first-light`, `emc` and `psr` have no missing mark; the copied TVAC boundary
does, while shipped TVAC remains observed and incomplete.

Resource migration: no schema or source Project/Actual/View edit. Regenerate
affected public Scene/SVG/PNG only with the public materializer; run all 21
contexts as one batch and inspect an exact generated-file diff. Any changed
semantic/diagnostic/contrast/font report is regenerated with its owner tool.
Compare rendered output visually as a batch. Focused tests and public batch
must pass before committing the code and generated evidence in one coherent
publication. Inspect the ensuing CI three-OS full pytest/conformance,
wheel/smoke and newest-Python reproduction; do not duplicate full local pytest.

## I476-2 — Acceptance and issue disposition

Publish an acceptance review separately with exact implementation commit,
commands, CI run, artifact diff summary and one direct-evidence row for each
literal criterion. Report the shipped/copy TVAC distinction explicitly. Close
#476 only after the issue owner corrects or confirms its contradictory TVAC
sentence and all three criteria are met. A new policy or layer gap returns to
a published design correction and plan amendment before further code.
