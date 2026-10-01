# Architecture Review - A gate that is derived from its dependencies (#788)

**Reviews:** [design](../../design/issue-788-derived-gate-design-2026-10-01.md) (plan:
[design plan](../../planning/active/issue-788-derived-gate-design-plan-2026-10-01.md); slices:
[implementation plan](../../planning/active/issue-788-derived-gate-implementation-plan-2026-10-01.md)).
**Base:** `main` at `648c4f9a` (2026-10-01).
**Reviewer note:** the same author wrote the design and this review. The review therefore attacks the design from the
repository's own constraints (checkers, existing code, adjacent specifications, the committed corpus) rather than from
taste, and it records what changed because of each finding. An independent read by the lead is requested before slice 1
starts, in particular of F1, F4, F5 and F6 and the open points in section 4.
This is a design review, not an issue acceptance review: it carries no literal acceptance table and no
`chrona:literal-acceptance` marker.

## 1. Verdict

**Proceed, with one slice published first and the rest gated.** The representation is sound and small: one new union
branch, no change to any existing definition, no change to View, Layout, Scene or adapters, and a derived gate that is
provably interchangeable with a fixed-point twin. Slice 0 (the better rejection) is independent of every decision below
and should merge first.

Three things the issue does not say, and the lead should decide knowingly:

1. **Almost no committed gate is a derivation.** 51 of 55 dependent fixed points sit later than their earliest feasible
   date; they are negotiated dates, not computations (F4). The owner's rule is an additional form; it should not be read
   as a cleanup of the corpus, and nothing should be converted.
2. **A derived gate cannot be wrong, so it cannot warn.** The commitment half of a fixed gate has to be re-stated
   (`at.max`, or `deadline`), and today `deadline` is inert and its specified warning was never built (F5, F6).
3. **"Derived" is not "forecast".** Actuals still never move the planned date (F11).

## 2. What was checked

- The issue (#788), the #148 go/no-go comment that found it, AGENTS.md (the sequence, the layer rules, Spec 56 section
  3.2), Specs 04, 05, 06, 12, 56, 65, and `core-v0.1-diagnostics.md`.
- Code: `scheduling/scheduler.py` (every function), `core/validation.py`, `core/attachments.py`, `core/diagnostics.py`,
  `core/relation_identity.py`, `app/cli.py` (diagnostic serialization), `usecases/project_checks.py`,
  `usecases/warning_ledger.py`, `presentation/model/projection.py` (mode and placement-shape reads), `terse/parser.py`,
  `compiler.py`, `ledger.py`, `diagnostics.py`, `tools/schema_equivalence.py`, `tools/corpus_coverage.py`.
- A scan of the 37 committed `timeline/v0.7` Projects (examples, conformance, skill example, test fixtures) for fixed
  points, their predecessors and `deadline` values (design plan section 1).
- Spikes outside the repository, working tree restored each time: the schema branch, a scheduler branch, validation and
  attachment edits; the S0 gate; twelve scheduling cases (design 11.2); a draft render of a derived gate and its fixed
  twin (byte-identical SVG).
- `gh pr list`: open PRs are #787 (the `chrona skill` command; edits `skills/chrona/references/diagnostics.md`,
  `app/cli.py`, `tests/fixtures/cli_characterization/golden.json`) and #424 (README). This pack's PR adds four new files
  and edits none of them. The implementation plan names the overlaps for later slices.

## 3. Findings

Severity: **B** blocking (changed the design), **M** material, **m** minor, **O** observation. "Resolved" means the
design text already carries the answer.

### F1 (B, resolved) A new union branch is not an "optional property" under Spec 56 section 3.2

Section 3.2 is written for optional properties and gives a mechanical rule for version bumps. A new tagged branch of a
discriminated union is neither. The S0 gate confirms the mismatch: it classifies the schema change as `changed` (not
`additive`, which is only property insertion) and fails closed until an L1 delta is listed. The repository has done the
same thing once, deliberately: View v0.28 widened an annotation anchor `endpoint` enum with `end` in place and listed the
delta ("every existing document stays valid and renders the same").
**Resolution:** in place, one declared L1 delta, one sentence added to section 3.2 naming a union branch as a widening
(design 9, L5). A `timeline/v0.8` bump was rejected: it widens nothing for readers and migrates every pinned document.
Residual risk: an older reader rejects a document that uses the new mode (`additionalProperties: false` on the old branch
set). That is true of any additive property and is not a regression.

### F2 (B, resolved) `amount: 0d` on `scheduled` is not a small change

It looks like a one-line relaxation and is not: the free-label `type` cannot gate it, the placement shape would depend on a
value, it targets different endpoints, it weakens `E_INVALID_AMOUNT` for tasks, and an anchored zero-length object is a
fixed point in disguise (design 3.1).
**Resolution:** rejected in favour of a new mode.

### F3 (M, resolved) The diagnostic model has no place for details, and adding one can break a subclass

`Diagnostic` is `(id, message, path)`. Adding a defaulted base field shifts the positional constructor of
`TerseDiagnostic`, which `with_source` builds as `TerseDiagnostic(self.id, self.message, self.path, self.range, ...)`: the
range would land in the new field. `TerseDiagnostic.as_dict` also builds its own dict and would drop `details`. The CLI
serializes in `_diagnostic` and `_reject`, and `Diagnostic.as_dict` is a third serializer used by the guided path.
**Resolution:** `details` is a keyword-only, non-hashed field of the Core `Diagnostic`; one shared serializer; the terse
class passes it through; a unit test constructs a `TerseDiagnostic` positionally and round-trips `details`. The #142
interface and the #148 S3 draft ingress both carry `Diagnostic` objects and must inherit `details` without code
(implementation plan slice 0).

### F4 (M, resolved) The corpus does not describe the owner's rule

Of 55 fixed points with predecessors, 4 sit exactly on their earliest feasible date and 51 later (27 of 30 in
`examples/`); for example HALCYON-1 `cdr` is 2027-05-07 against 2027-04-06 allowed. These gates are commitments with
slack. Converting one to a derived gate would either move it to the earlier date or require a floor equal to today's
date, which then moves silently the day a predecessor passes it instead of rejecting.
**Resolution:** no committed gate converts; a conversion is never automatic; the design says the form is for new gates
whose rule is the date (non-goal, design 12). The twin property (I1) is what makes a deliberate conversion safe to do by
hand: substitute the derived date and the plan is identical.

### F5 (M, resolved with a gate) A derived gate cannot fail, so a slip becomes silent

A fixed gate told the author when work no longer fit (the rejection of the issue). A derived gate moves instead. Without
an expressed promise a project can slip a year and the gate follows it quietly. Two remedies exist and they differ in a way
that matters: a hard cap (`at.max`) rejects the plan, and a rejected plan returns no placements and `render` refuses it, so
the project that is slipping can no longer be drawn; a soft promise (`deadline`) would warn and still draw.
**Resolution:** ship `at.max` with the form (free), keep `deadline` inert in the scheduler (Q-SCHED-2), and gate the soft
form as slice 3 (L4). The design states the two intents side by side (design 6.3) so an author is told which tool does
which job.

### F6 (M, open) `deadline` is stored, specified, and has no consumer; `W_DEADLINE` was never built

`deadline` appears in the schema, Spec 04 section 10, Spec 05 section 9 and Q-SCHED-2, and in 11 committed values. No
scheduler, validation, View, Layout, Scene or adapter code reads it. `W_DEADLINE` is a documented identifier, and Spec 04
section 23 lists "deadline diagnostics" in the conformance subset a scheduler MUST support, yet nothing emits it: the
reference scheduler is out of step with its own specification, independent of #788. Three pieces are missing for the pair
"derived gate plus deadline": the evaluation (a pure function over placements, precedent `attachment_warnings`), a warning
channel (`ScheduleResult.diagnostics` are all errors; warnings travel through `warning_ledger` to `render` only), and a View
concept (no deadline mark or role exists).
**Disposition:** the evaluation and the `render` warning are slice 3. The `chrona schedule` JSON field is an agent-interface
result shape (#142) and is not decided here. The View concept is a successor issue. The review does not recommend
treating the missing `W_DEADLINE` as part of #788's acceptance.

### F7 (M, resolved) Calendar snapping and the twin invariant

Spec 04 section 21 normalizes the start of a scheduled span; it is silent about a point. Snapping the derived date to a
working day would make a derived gate and its fixed twin differ (the twin could not sit where the derived date skipped),
and would break "one day earlier is rejected". Not snapping has a visible cost: `+2d` from a Friday is a Sunday (spiked).
**Resolution:** no snapping; `wd` lags are the author's tool; a later optional `snap` is additive (L7). The Sunday case is
a golden test so the behaviour is deliberate, not accidental.

### F8 (M, resolved) The terse form bends one rule and the owner's sketch is ambiguous

Spec 65 S3 says the kind does not constrain the schedule form; `launch gate after qa +2wd` is the first construct where
the kind (`gate`) selects it. That is acceptable only if recorded: normalisation N7 in Spec 65, narrowing (not retiring)
`E_TERSE_SCHEDULE_REQUIRED`. The sketch `gate after qa +2wd >= 2027-05-07` binds ambiguously in a comma list and names no
endpoint; the design uses `at >= D` in the schedule slot. The ledger test fails until new schema paths are classified, so
slice 1 must classify them `yaml-only` or the schema slice breaks an unrelated test. The terse slice edits the same
documents as #148 S4 (Spec 65, the guide and its error table) and is sequenced after it.
**Resolution:** design section 8 and implementation plan slice 2.

### F9 (M, resolved) Cycles, `validate`, and #780

`validate` does not detect dependency cycles; `schedule` does (#780). Derived points make cycles easier to write (a gate
inside a group that depends on the group's end is a cycle, spiked). Re-implementing cycle detection in `validate` for the
new mode would duplicate #780 and diverge from it.
**Resolution:** cycles stay `schedule`'s, with the same codes and pointers as for spans; two goldens pin them; the static
"nothing to derive from" check lives in `validate_project` with the existing `E_DERIVATION` (no new code), because it is a
property of one object plus a relation count and the two commands should agree (L9).

### F10 (m, resolved) Float and critical path change meaning for plans that adopt the form

A slack fixed gate dwarfs a chain, so total float stops describing the plan (spiked: critical `{a, g}`, `b` 35, `c` 30). A
derived gate that ends the chain restores it (`{a, c, g}`, `b` 5). `_latest_at_target` and `_cap_latest_endpoint` already
have point branches that no object reaches; slice 1 must test them and make `_latest_at_target` honour `at.max`. Corpus
output is unchanged (no adopter).
**Resolution:** design 5.4 and golden G8.

### F11 (m, resolved) "Derived" must not read as "forecast"

Actuals never feed the scheduler (Spec 04 section 17, Spec 06 section 8.2). A late predecessor Actual does not move a
derived gate; editing the plan does. The `+3d` label is actual minus planned, unchanged. A reader of "scheduled gate" could
reasonably expect forecasting.
**Resolution:** one sentence in Spec 04 (slice 1) and the guide; no mechanism. Rescheduling from Actuals stays a deferred
policy (non-goal).

### F12 (m, resolved) A pointer that does not exist, and what the diagnostic promises

For a relation without an `id`, `E_FIXED_TARGET_VIOLATION` points at `/relations/<target object id>`, which is not a
pointer into the Project (`validate_project` uses the index). Slice 0 changes only that fallback. What is contract after
slice 0: the code, one diagnostic per violating relation, the pointer for relations with an id, the `details` keys listed
in design 4.3 (additive thereafter). The message text is **not** contract (Spec 65 section 6.1: "messages and hints may be
improved without a version change"); the exact-text fixtures pin it for review, not for compatibility.

### F13 (m, open) Overlapping and derived files

Derived documents change on main, never in a PR: `docs/examples/corpus-coverage.md` (a new uncovered row),
`docs/diagnostics/inventory.md` (moved source locations). `skills/chrona/references/diagnostics.md` is edited by #787 and by
slice 4; `app/cli.py` and `golden.json` by #787 and slice 0; `docs/guides/terse-plan.md` and Spec 65 by #148 S4 and slice
2. Each slice re-checks `gh pr list` and rebases immediately before merge (implementation plan, section 8).

### F14 (m, resolved) The issue omits attachment

`attachesTo` requires a `fixed-point` source (`core/attachments.py`). A derived milestone is the natural thing to attach to
a campaign (#486, #517, #518); without a change, attaching one is `E_PROJECT_ATTACH_SOURCE_NOT_POINT`.
**Resolution:** allow either point mode as a source; the host test treats either as a point. `W_PROJECT_ATTACHED_OUTSIDE_HOST`
already works from placements (spiked).

### F15 (m, resolved) The schema error for a bad schedule now lists five forms

Structural validation of an invalid `schedule` reports the allowed tags (Spec 56 section 3, step 3). Adding a tag changes
that message. The S0 L3 run showed no probe is affected, and no test asserts the live list of forms (the exact-message
asserts are on synthetic schemas; one CLI test asserts only the prefix `expected one permitted form`). `skills/chrona/references/diagnostics.md` describes the message and lists the modes: slice 4 updates it.

### F16 (O) Fixed-span targets get a per-endpoint answer

For a `fixed-span` target, `earliest` is the bound for one endpoint; moving a span's start alone changes its length. The
message says "earliest feasible date for build.start" and does not claim a re-placement. Acceptable: the case in the issue
is a point.

### F17 (O) The issue's acceptance says "or"

Slice 0 meets the second branch ("the scheduler's rejection tells them the date to write") with the issue's own test shape.
The owner's direction is the first branch. Whether the issue closes on slice 0 or on slice 1 is a lead decision (L1); the
recommendation is to keep it open.

## 4. Open points for the lead

1. L1: when does #788 close (design 13).
2. L2 and L3: the name `scheduled-point` and whether `at.max` ships (F5).
3. L4: whether `W_DEADLINE` is built and, in particular, how it reaches `chrona schedule` JSON, which is #142's shape.
4. L5: in place versus a `timeline/v0.8` bump (F1).
5. L6: the terse spelling and the dependency on #148 S4 (F8).
6. L7 and L9: no snapping; the static check in `validate`.
7. L8: whether any public example should teach the form (recommendation: no).

## 5. Conditions carried into the implementation plan

1. Slice 0 merges alone and changes no verdict; its sweep proves every committed Project's outcome is identical except the
   message and `details` of `E_FIXED_TARGET_VIOLATION` on plans that already rejected.
2. `details` is keyword-only and non-hashed on `Diagnostic`, serialized in one place, passed through by `TerseDiagnostic`.
3. Slice 1 lands schema, validation, scheduler, attachment, conformance, goldens, properties, the L1 delta, two probe
   sites, the terse-ledger classification, and Specs 04, 05, 56 in one PR, because any subset leaves a red gate (the ledger
   test, the delta, or a spec that contradicts the schema).
4. No slice edits a derived document or an existing example.
5. Slice 2 waits for #148 S4. Slice 3 waits for the lead's L4 and for #142's result shape. Slice 4 rebases on #787.
6. The twin invariant I1 is a property test, not a hand-checked example.

## 6. Rejected alternatives (with the reason)

| Alternative | Why not |
| --- | --- |
| `scheduled` with `amount: 0d` | F2 |
| `fixed-point` with `at` optional | One mode, two authorities; `fixed` stops meaning fixed |
| A relation flag or a `derivations` section | Authority is per object; a second owner of a completed date |
| Snapping the derived date to a working day | Breaks the twin and minimality invariants (F7) |
| Reading `deadline` in the scheduler as a bound | Violates Q-SCHED-2; a promise would silently become a constraint |
| Enforcing the promise only with `at.max` | A slipping plan could no longer be drawn (F5) |
| Converting committed gates | Moves dates or drops slack (F4) |
| A `timeline/v0.8` bump | Migrates every pinned document for a widening (F1) |
| Cycle detection in `validate` for the new mode | Duplicates #780 (F9) |
| A kind-neutral keyword in terse | Longer in the case the issue shortens; the bend is recorded instead (F8) |
| `details` on one serializer only | The #142 interface and the draft ingress would diverge (F3) |

## 7. Whole-architecture check

- **Layers.** The change sits in Core (schema, validation, attachments, diagnostics) and the scheduler. View, Layout, Scene,
  adapters and `tools/check_import_direction.py`'s allow-table are untouched: no new import is introduced. The terse
  compiler still imports only `chrona.core` and repeats no Core rule (it emits the mode; Core owns every check).
- **Authority.** One authority per object remains: fixed, scheduled, scheduled-point, rollup. `deadline` stays a stored
  target that is evaluated, never a bound (Q-SCHED-2). Fixed placements are still never silently moved.
- **Determinism.** The date rule is a max over a set; I4 (order independence) is a property test; Spec 04 section 19 holds.
- **Compatibility.** Every existing document keeps its verdict and placements; only plans that already rejected with
  `E_FIXED_TARGET_VIOLATION` read differently. Older readers reject the new mode, as for any additive property.
- **Extension points.** `scheduled-point` works for any `type` label. A future optional `snap`, a derived span (a
  non-goal), or a deadline mark each fit as an additive change.
- **Adjacent designs.** #148: ledger classification and terse slice sequencing (F8, F13). #142: `details` serialization and
  the `W_DEADLINE` result shape (F3, F6). #780: cycles stay `schedule`'s (F9). #486, #517, #518: attachment (F14).
- **Documentation.** The living specifications (04, 05, 56, 65) are updated by the slices that change behavior; this pack
  duplicates no normative rule beyond the design contract it names.
