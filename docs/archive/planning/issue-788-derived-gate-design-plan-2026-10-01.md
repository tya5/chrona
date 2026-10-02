# Design Plan - A gate that is derived from its dependencies (#788)

**Status:** In design. This is step 2 of the AGENTS.md sequence; the
[design](../../design/issue-788-derived-gate-design-2026-10-01.md), the
[architecture review](../reviews/issue-788-derived-gate-architecture-review-2026-10-01.md) and the
[implementation plan](issue-788-derived-gate-implementation-plan-2026-10-01.md) are published in the same
docs-only PR. No product code, schema, specification or example changes here.

**Owner direction (recorded, not re-opened):** "even a gate should support a scheduled form." Option 1 of the
issue (a point whose date is derived from its dependencies) is wanted. Option 2 (a better
`E_FIXED_TARGET_VIOLATION`) is the cheap first slice either way. What this pack decides is *how*, not *whether*.

## 1. Baseline (what is published, what is inferred, what is unverified)

Published and verified against `main` at `648c4f9a` (2026-10-01):

- **The gap.** Project v0.7 (`schemas/project-v0.7.schema.yaml`, `$defs/schedule`) has four modes:
  `fixed-point` (`at`), `fixed-span` (`start`, `end`), `scheduled` (a positive `amount`, optional `anchor`,
  `constraints`) and `rollup`. A `scheduled` object is always a span: its placement is `{start, end}`. A point
  can only be `fixed-point`, and a dependency into a fixed object is a validation condition, never a placement
  input (Spec 04 section 15.1; `_validate_fixed_targets` in `src/chrona/scheduling/scheduler.py`).
- **The rejection says too little.** `E_FIXED_TARGET_VIOLATION` carries the message "Fixed target violates
  dependency lower bound" and the pointer `/relations/<id>` (or `/relations/<target object id>` when the relation
  has no `id`). It does not name the gate, the date it was given, the date it needed, or the predecessor. The
  scheduler computes that date (`required`) and throws it away. `chrona schedule` returns no placements for a
  rejected plan, so the author has nothing else to read.
- **The consumers of a schedule mode are few.** Outside the schema and Spec 04/05, the mode string is read in
  `core/validation.py`, `scheduling/scheduler.py`, `core/attachments.py`, `presentation/model/projection.py`
  (only `rollup`), and the terse compiler (`terse/parser.py`, `compiler.py`, `ledger.py`). The View, Layout and
  Scene consume *placements*, and tell a point from a span by the placement shape (`"at" in planned`), not by the
  mode (`build_review_projection`). Section 3 of the design lists each consumer.
- **`deadline` exists and does nothing.** `deadline` is an optional date on every object (schema, Spec 04 section
  10, Spec 05 section 9, Q-SCHED-2). No scheduler, validation, View, Layout or Scene code reads it (`grep deadline
  src schemas` finds only the terse ledger entry and the schema). `W_DEADLINE` is listed in
  `docs/specification/supplemental/core-v0.1-diagnostics.md` and Spec 04 section 23 puts "deadline diagnostics" in
  the conformance subset a scheduler must support, yet no code emits it.
- **Committed gates are mostly commitments, not derivations.** A scan of the 37 committed `timeline/v0.7`
  Projects (examples, conformance, skill example, test fixtures; archive and generated output excluded) finds 83
  `fixed-point` objects, 55 of which have predecessors. Only 4 sit exactly on their earliest feasible date; 51 sit
  later (for example HALCYON-1 `cdr`: predecessors allow 2027-04-06, the gate is 2027-05-07). In `examples/` the
  figure is 27 later and 3 exact. Of the 11 committed `deadline` values, 10 are on a fixed point and 1 on a scheduled
  span; every one is on or after the object's planned date. Nothing in the corpus needs converting, and a naive
  conversion would change dates (design section 6).
- **Attachment and Actuals take the planned date from placements.** `attachesTo` is checked against
  `fixed-point` in `core/attachments.py`. A point Actual is `actual: {at: ...}`, compared with the planned `at` by
  `ReviewItem.at_delta` (Spec 06 section 8). Actuals never feed the scheduler (Spec 04 section 17; Spec 06
  section 8.2).
- **#148 context.** The terse syntax (`chrona compile`, Spec 65) compiles a gate only as `gate DATE`; a gate with no
  date is `E_TERSE_SCHEDULE_REQUIRED`. Another agent is implementing #148 S3 and S4 (draft ingress, docs), which edit
  `docs/guides/terse-plan.md` and Spec 65.

Inferred (cited in the design where used): that the schedule-mode string is read nowhere else (checked by grepping
`fixed-point`, `fixed-span`, `"scheduled"` and `"rollup"` over `src/`, `schemas/`, `tools/`, `conformance/`);
that no public slide changes (nothing can use a mode that does not exist, and no committed Project is edited).

I also ran throwaway spikes outside the repository (not committed, working tree restored after each): the schema
branch, a 25-line scheduler branch, and a validation and attachment change were applied locally. They produced
the golden values in the design, showed the schema-equivalence gate output (one L1 delta, L2 and L3 unchanged), and
rendered a derived gate and its fixed-point twin to byte-identical SVG with no View, Layout or Scene change. They
are evidence that the approach is sound, not product code.

Unverified until implementation: the terse grammar's behaviour with real agents (the #148 go/no-go method should be
re-run after the terse slice); how the W_DEADLINE warning should reach `chrona schedule` JSON, which is the
agent-interface result shape owned by #142.

## 2. Literal acceptance inventory

#788 has one acceptance line, plus the owner's decision. Each row is answered where shown; the release review will
carry one row per line.

| # | Literal requirement (source) | Answered in |
| --- | --- | --- |
| A1 | "An author can state a gate that follows a task without writing its date, **or** the scheduler's rejection tells them the date to write" (issue, Acceptance) | design 4 (slice 0 answers the second branch), design 3 and 5 (the first branch) |
| A2 | "covered by a test with a fixed-point gate behind a duration task" (issue, Acceptance) | design 4.4, 11.2; implementation plan slice 0 and slice 1 |
| A3 | Option 1: a point whose date is computed from its dependencies, with an optional not-earlier-than bound and no stored date (issue, Decide 1) | design 3, 5 |
| A4 | "a Project schema change (a new schedule mode, Spec 56 section 3.2: additive and optional in place, if absent means today's behaviour)" (issue) | design 3.5, 9 |
| A5 | "a scheduler change" (issue) | design 5 |
| A6 | "a Scene/View consequence (a point whose date moves)" and "related to attached milestones (#517, #518) and to the as-of/actual handling of a gate that slips" (issue) | design 7 |
| A7 | Option 2: `E_FIXED_TARGET_VIOLATION` names the earliest feasible date and the relation that forces it (issue, Decide 2) | design 4 |
| A8 | "even a gate should support a scheduled form" (owner decision) | design 3 |
| A9 | "Related: #148, #142, #780" (issue) | design 5.3, 8, 13; review F9 |

Whether the issue may close after slice 0 alone (A1's second branch) or only after the derived form lands (the owner's
direction) is a decision for the lead (design 13, L1).

## 3. Use cases

1. **Author states the rule, not the date.** "The launch gate falls two working days after QA ends" is one
   statement. When QA grows, the gate moves; nothing is recomputed by hand.
2. **Author states a floor.** "...but not before 2027-05-07" (a regulator window, a trade show).
3. **Author states a promise separately.** "...and the launch must not slip past 2027-06-30." Two readings exist,
   a hard cap that rejects the plan and a soft target that the chart shows being missed. Design section 6.
4. **Agent or author with a wrong guess is told the answer.** Slice 0: the rejection names the date to write.
5. **Reviewer compares plans.** A baseline or a scenario shows the derived gate moving when work moves, which a
   fixed gate cannot do (it rejects instead).
6. **Reporter records the gate happening.** `actual: {at: ...}` against the derived planned date, unchanged.
7. **Author keeps today's behaviour.** A committed gate on a negotiated date stays `fixed-point`; nothing migrates.

## 4. Open decisions (answered in the design, each with a recommendation)

| # | Decision | Design |
| --- | --- | --- |
| D1 | Representation: `amount: 0d` on `scheduled`, a new mode, or something else; and its name | 3 |
| D2 | What the derived point may carry (floor, cap, nothing else) | 3.3 |
| D3 | Semantics of the date: arithmetic, calendar, snapping, failure cases | 5 |
| D4 | How "must not slip past D" is expressed beside a derived date | 6 |
| D5 | Critical path, float and driving relations through a derived point | 5.4 |
| D6 | Scene/View, Actual, baseline, scenario and attachment consequences | 7 |
| D7 | Diagnostic improvement as slice 0: exact message and fields | 4 |
| D8 | Terse syntax for the derived gate, its floor and cap | 8 |
| D9 | Schema evolution: in place, and the Spec 56 wording it needs | 9 |
| D10 | Proof plan, including the S0 schema-equivalence output | 11 |
| D11 | Slice order | implementation plan |

## 5. Responsibility boundaries

- **Project (Core)** owns the new mode, its validation and the date rule. **Scheduler** computes the date.
  **Validation** owns endpoint availability and the static "nothing to derive from" check. Nothing else in the
  Core changes meaning.
- **View, Layout, Scene, adapters** change nothing. They already consume placements. Any new mark (a deadline mark)
  is a separate View decision and is out of scope here (design 6.4).
- **Terse compiler** maps one new construct to the new mode and repeats no Core rule (Spec 65 section 1).
- **Diagnostics** gain an additive, optional `details` object; codes stay stable.

## 6. Data and resource model, and migration effects

- One new optional schedule form in `project-v0.7` (in place, no version bump); no new resource, no new schema
  file, no store change.
- No committed Project, example, snapshot, Actual Set, View, Theme or Layout changes. Derived reports that
  enumerate schema values (`docs/examples/corpus-coverage.md`) gain one uncovered row when the schema lands; that is
  regenerated by the main sync and never hand-edited.
- Wheel, CLI, JSON result and skill documentation changes are listed per slice in the implementation plan.

## 7. Design review questions

The architecture review must answer at least: (a) is a new mode really additive under Spec 56 section 3.2, given the
rule's wording is about optional properties; (b) does any consumer branch on "not fixed means scheduled span";
(c) does the owner's rule change the meaning of an existing document; (d) can the derived form hide a plan error that
the fixed form exposed; (e) does `deadline` stay inert as Q-SCHED-2 requires; (f) how does the slice order interact
with #148 S3/S4 and #142; (g) what in `E_FIXED_TARGET_VIOLATION`'s shape is a compatibility promise.

## 8. Acceptance evidence needed

Scheduler equivalence on every committed Project (no verdict or placement changes); golden scheduling cases;
property tests (substitution, minimality, monotonicity, order independence); the S0 schema-equivalence output with
the one listed L1 delta and no L2 or L3 change; conformance; byte-identical regenerated public examples; the
exact-text diagnostic fixtures for slice 0.

## 9. Order of design slices

1. This pack (plan, design, review, implementation plan), one docs PR.
2. Lead decisions L1 to L9 (design section 13).
3. Implementation slices 0 to 4 as in the implementation plan, each its own PR.
