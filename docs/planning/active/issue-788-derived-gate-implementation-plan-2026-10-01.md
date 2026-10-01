# Implementation Plan - A gate that is derived from its dependencies (#788)

**Status:** Proposed. Step 4 of the AGENTS.md sequence, published with the
[design plan](issue-788-derived-gate-design-plan-2026-10-01.md), the
[design](../../design/issue-788-derived-gate-design-2026-10-01.md) and the
[architecture review](../../reviews/current/issue-788-derived-gate-architecture-review-2026-10-01.md). It is final
only after the lead's decisions L1 to L9 (design section 13) and an independent read of the review.
**Base:** `main` at `648c4f9a` (2026-10-01). Every code slice is its own PR, `Refs #788` only, with no closing keyword in
a title, body or commit.

## 0. Why this order

Slice 0 depends on nothing: it needs no schema, no decision, and it is the issue's own acceptance on its own. Slice 1 is
the smallest change that gives the owner's rule, and it is indivisible: the schema, validation, scheduler, attachment,
conformance cases, the schema-equivalence delta and the terse-ledger classification each turn a repository gate red when
landed alone. Slice 2 (terse) waits for #148 S4 because both edit Spec 65 and the terse guide. Slice 3 (the soft promise)
is lead-gated and must agree its JSON shape with #142. Slice 4 is teaching: skill and guides, after the code they
describe; #787 (the skill command) has merged.

## 1. Slice overview

| Slice | Content | Depends on | Lead gate |
| --- | --- | --- | --- |
| 0 | `E_FIXED_TARGET_VIOLATION` names the earliest feasible date and the forcing relation (`details`) | none | none |
| 1 | `scheduled-point`: schema, Core, scheduler, attachment, conformance, proofs, specs | slice 0 merged (shares `scheduler.py` and the diagnostics path) | L2, L3, L5, L9 |
| 2 | Terse: `gate after X`, `at >= D`, `at <= D` | slice 1, #148 S4 merged | L6 |
| 3 | `W_DEADLINE` (the soft promise) | slice 1; #142 result shape agreed | L4 |
| 4 | Teaching: skill references, guides, CLI reference | slices 0 to 2 (3 if built) | L8 |

## 2. Slice 0 - the better rejection

**Goal.** An author or agent who guessed a gate's date reads the date to write and the relation that forces it, in one
step. Meets the second branch of the issue's acceptance; changes no verdict.

**Files.**

- `src/chrona/core/diagnostics.py`: add `details: Mapping[str, Any] | None`, keyword-only, excluded from hashing and
  equality ordering concerns (check that no code puts a `Diagnostic` in a set or uses it as a key before choosing
  `compare`/`hash` flags); `as_dict` omits it when `None`.
- `src/chrona/scheduling/scheduler.py`: `_validate_fixed_targets` computes, per target endpoint, the maximum `required`
  over all relations into it and the relation giving it (first in relation order on a tie), then emits the existing code
  with the exact message and `details` of design 4.2 and 4.3. The relation key is the declared `id`, else `/relations/N`;
  the id-less pointer fallback becomes `/relations/N`.
- `src/chrona/usecases/failure_report.py`: `diagnostic_record` takes `details` and emits it only when present, after
  `message`; `rejection_report` passes `item.details`. `src/chrona/app/cli.py`: the `review` command's mapping of
  `Diagnostic.as_dict()` forwards it. One record builder; no second serializer.
- `src/chrona/terse/diagnostics.py`: `TerseDiagnostic.as_dict` and `with_source` carry `details`.
- `docs/specification/04-scheduling-model.md` section 20.1 (the diagnostic names the endpoint's earliest feasible date and
  the forcing relation; `details` keys), `docs/specification/supplemental/core-v0.1-diagnostics.md` (the row and the
  optional-details sentence). Spec 65 section 6.1 gains one sentence that Core diagnostics may carry `details`.

**Tests.**

- `tests/unit/chrona/scheduling/test_fixed_target_details.py` (new): the issue's case (design 4.4) with exact message and
  every `details` key; substituting `earliest` is accepted; one day earlier is rejected; two violating relations of
  different strength (both diagnostics carry the same `earliest` and `forcedBy`, each its own `required`); an id-less
  relation (`/relations/N` pointer and message spelling); a negative lag (`- 2d`); a calendar-qualified lag
  (`+ 2wd in six`); a `fixed-span` target; an unchanged count of diagnostics.
- `tests/unit/chrona/terse/test_diagnostics.py`: construct `TerseDiagnostic` positionally, round-trip `details` through
  `with_source` and `as_dict`.
- `tests/cli/test_cli.py` and the `failure_report` unit tests: `chrona schedule` JSON for the case, with and without
  `details`; every other diagnostic record unchanged (the six keys, same order).
- Existing `test_chrona_skill_diagnostics` case `fixed-target` and `tests/integration/test_conformance.py` stay green.

**Proof.**

- Scheduler sweep over all committed Projects, scenarios and snapshots before and after (canonical JSON of placements,
  diagnostics, analysis): identical for every Project; the only difference class allowed is the message and `details` of
  `E_FIXED_TARGET_VIOLATION` on plans that already rejected (the committed corpus has none, so expect zero differences).
  The sweep is a `corpus`-marked test with a synthetic twin, per AGENTS.md; its output is pasted in the PR.
- `python conformance/run_conformance.py`, `python tools/regenerate_public_examples.py --check --jobs 4` (byte identity).

**Must not.** Change which plans are rejected, the number of diagnostics, a code, or a pointer other than the id-less
fallback; return placements for a rejected plan; suggest or apply a correction; promise a feature in a hint; edit
`skills/chrona/references/diagnostics.md` (slice 4) or any derived document.

**Publication.** One PR. Acceptance evidence for the issue row: the test of design 4.4.

## 3. Slice 1 - `scheduled-point`

**Goal.** A gate whose date is derived, with an optional floor and cap, proven interchangeable with its fixed twin.

**Files.**

- `schemas/project-v0.7.schema.yaml`: the `scheduledPoint` definition, the fifth `schedule` branch, one example
  (design 3.4). No other definition changes; no shared part changes.
- `src/chrona/core/validation.py`: `_schedule_endpoints` returns `{at}` for `scheduled-point`; a static check that a
  `scheduled-point` has at least one relation into `at` or a `constraints.at.min` (`E_DERIVATION`, path
  `/objects/<id>/schedule`, message "Scheduled point has no predecessor and no minimum date").
- `src/chrona/core/attachments.py`: a source may be `fixed-point` or `scheduled-point`; a host that is either is "not a
  span"; the message of `E_PROJECT_ATTACH_SOURCE_NOT_POINT` says "a point object".
- `src/chrona/scheduling/scheduler.py`: a `scheduled-point` branch in the placement loop using `_lower_bound` unchanged
  (waits for sources, folds relations and `at.min`); places `{at: max}`; `E_CONTRADICTORY_BOUNDS` with `details` for
  `at.max`; `_latest_at_target` honours `at.max`. The `else` path that reports `E_ROLLUP_SCHEDULE` for an unknown mode
  stays for modes that are genuinely unknown.
- `src/chrona/terse/ledger.py`: classify `schedule.scheduled-point.*` and `constraints.at.*` as `yaml-only` ("not
  spellable yet"); the terse ledger test fails until this is done.
- `conformance/conformance-v0.1.yaml`, `tests/integration/test_conformance.py`: the derived-point authority cases.
- `conformance/schema-equivalence/expected-deltas-v0.1.yaml`: one L1 entry (`before` the four dereferenced branches,
  `after` the five); `tools/schema_equivalence.py`: two `ProbeSite` entries (the `min` and `max` date sites) on a new inline
  base document; `conformance/schema-equivalence/baseline-results-v0.1.json` re-recorded, adding rows and changing none.
- Specs: `04-scheduling-model.md` (sections 2.1/2.3 a derived point; 4 endpoints; 15.1; a new 20.4 "Scheduled point" with
  the rule, the no-snapping statement and the "derived is not a forecast" sentence; 23 conformance), `05-project-format.md`
  (the form, its two properties, `attachesTo`), `56-schema-authoring-and-diagnostics.md` section 3.2 (the union-branch
  sentence), `supplemental/core-v0.1-diagnostics.md`.

**Tests.**

- `tests/unit/chrona/scheduling/test_scheduled_point.py` (new): the golden cases G1 to G12 of design 11.2 with the exact
  dates and codes.
- `tests/unit/chrona/scheduling/test_scheduled_point_properties.py` (new, Hypothesis): I1 twin substitution, I2 minimality
  (with `earliest` equal to the derived date), I3 monotonicity, I4 order independence, "a derived point is never rejected as
  a fixed target".
- `tests/unit/chrona/core/test_attachments.py`: attach a derived point; derived host rejected; outside-host warning.
- A scenario test: a scenario adding a dependency moves a derived gate and rejects the fixed twin.
- `tests/unit/chrona/terse/test_ledger.py` green; `tests/unit/tools/` schema-equivalence tests for the delta and probes;
  schema-annotation lint green.

**Proof.**

- Scheduler sweep over every committed Project (identical placements, diagnostics, analysis; none uses the mode).
- `python -m tools.schema_equivalence --base-rev origin/main` pasted: `L1 ... delta` for `project-v0.7.schema.yaml`,
  L2 and L3 unchanged, runtime within budget (the spike measured 30 s of a 60 s budget).
- Conformance; `python tools/regenerate_public_examples.py --check --jobs 4` byte-identical; no file under `examples/` or
  any `generated/` directory in the diff; the render twin check (a derived gate and its fixed twin render byte-identical
  SVG) as a test in `tests/integration/`.
- Import-direction and module-reachability checks.

**Must not.** Read `deadline` anywhere; snap the derived date to a working day; accept `start`/`end` endpoints on the new
mode; add `anchor` or `amount` to it; convert or edit any committed Project or example; add a code beyond `E_DERIVATION`
and the existing `E_CONTRADICTORY_BOUNDS`; detect cycles in `validate` (#780); read the object `type`; change a shared
schema part; edit a derived document.

**Publication.** One PR. Derived documents (`corpus-coverage.md`, `diagnostics/inventory.md`) regenerate on main.

## 4. Slice 2 - terse syntax

**Goal.** `launch "Launch" gate after qa +2wd` compiles to the derived form; floors and caps are spellable.

**Depends on** #148 S4 merged (it edits the same Spec 65 text and `docs/guides/terse-plan.md`); re-check `gh pr list`.

**Files.** `src/chrona/terse/parser.py` (gate with no schedule words and `after`; `pointbound` clauses `at >= D`,
`at <= D`; narrowed `E_TERSE_SCHEDULE_REQUIRED` messages and hints), `compiler.py` (the mode, `constraints.at`, target
endpoint `at`, predecessor default endpoint `.at`, source-map entries of design 8.1 T6), `ledger.py` (flip the slice 1
entries to `mapped`), `docs/specification/65-terse-plan-syntax.md` (grammar, S3, 3.3, section 4 mapping, normalisation N7,
codes), `docs/guides/terse-plan.md` (the table row `pdr gate`, one example with a derived gate, one with a floor; the
documented-commands check reads this file), and the fixtures under `tests/fixtures/terse/`.

**Tests.** Parser and compiler cases for T1 to T6, every narrowed `E_TERSE_SCHEDULE_REQUIRED` form, `after` on a derived
predecessor, `.start` on it (Core's mismatch), positioned errors; the property test of the compiler (no
`E_TERSE_COMPILER_DEFECT`) extended with derived gates; the HALCYON-1 twin unchanged (its gates are fixed with slack);
the doc-check on the guide.

**Proof.** Compile-twin tests; the #148 go/no-go method re-run with three fresh agents on a plan that needs a derived gate
(recorded on #148, not here); conformance; byte identity.

**Must not.** Add a keyword other than reusing `at`; accept a bound without an `after` clause; derive a `task`; compute a
date in the compiler; change any other grammar rule.

## 5. Slice 3 - `W_DEADLINE` (the soft promise, L4 applied)

Specified and tracked in the [#792 work record](issue-792-deadline-warning-work-record-2026-10-02.md), which supersedes the
file list and tests that stood here: a pure Core function over placements (`core/deadlines.py`), surfaced in `chrona schedule`
(`warnings`), MCP `schedule_project` (`warnings`) and `render` (stderr ledger); `validate` unchanged; the scheduler never reads
`deadline`; the View mark and the terse clause are successor #822.

## 6. Slice 4 - teaching

**Files.** `skills/chrona/SKILL.md`, `skills/chrona/references/authoring-model.md` (the fifth mode, when to use fixed versus
scheduled-point, the floor and cap, the promise pair), `skills/chrona/references/diagnostics.md` (the `E_SCHEMA` list of
forms; the `E_FIXED_TARGET_VIOLATION` row now names the earliest feasible date and `details`; `E_DERIVATION` and
`E_CONTRADICTORY_BOUNDS` for the point), `docs/guides/cli-reference.md` (the optional `details` object),
`docs/guides/progressive-project-tutorial.md` only if the lead chooses to teach it (L8). Re-check `gh pr list`: #787 (merged) edited the
diagnostics reference and the skill library.

**Tests.** The skill diagnostics test; the documented-commands check; the wheel skill test.

**Must not.** Add a public example or edit any `examples/` file unless L8 says so, in its own PR with its generated evidence.

## 7. Gates and commands every code slice runs

```bash
.venv/bin/python -m pytest -q <focused tests of the slice>
.venv/bin/python conformance/run_conformance.py
.venv/bin/python tools/regenerate_public_examples.py --check --jobs 4
.venv/bin/python -m tools.schema_equivalence --base-rev origin/main        # slice 1; paste the output
.venv/bin/python tools/check_import_direction.py
.venv/bin/python tools/check_module_reachability.py
.venv/bin/python tools/check_issue_acceptance_reviews.py
```

Full pytest and the three-OS matrix run in CI. No slice edits `docs/diagnostics/inventory.md`,
`docs/diagnostics/declared-value-inventory.md`, `docs/diagnostics/vocabulary-inventory.md`,
`docs/gallery/presentation-coverage.md`, `docs/examples/corpus-coverage.md` or `examples/*/generated/*`; main regenerates
them. Commit trailers and the "Refs only" rule apply to every commit and every squash body.

## 8. Coordination and publication

- Before editing a shared file, run `gh pr list -R tya5/chrona --state open --json number,title,files` and rebase right
  before merge. Known overlaps: #787 has merged (it edited `app/cli.py`, `golden.json`,
  `skills/chrona/references/diagnostics.md` and `tests/unit/chrona/skills/test_chrona_skill_diagnostics.py`), so slices 0
  and 4 start from its result, and any later skill or CLI PR is re-checked; #148 S3/S4 (Spec 65, the terse guide,
  `src/chrona/terse/`) against slice 2; any #142 slice against `usecases/` and the CLI result shape (slices 0 and 3).
- #454 is the reviewer's board: read it to pick work, never edit or comment on it.
- Each slice is a separate publication with its own CI evidence; the acceptance review for #788 is written only after the
  slices the lead selected have merged, and cites the three-OS run on the commit that contains the review.

## 9. Acceptance and release

Literal acceptance of #788 and its evidence:

| Row | Evidence | Slice |
| --- | --- | --- |
| The scheduler's rejection tells the author the date to write | Test of design 4.4 | 0 |
| An author can state a gate that follows a task without writing its date | Golden G1 and the twin render test | 1 (terse spelling: 2) |
| Covered by a test with a fixed-point gate behind a duration task | `test_fixed_target_details.py`, `test_scheduled_point.py::G1` | 0, 1 |

The issue stays open until the lead's L1 decision is applied. The release review states the S0 gate output, the
sweep result, and the derived-document diffs the main sync produced.

## 10. Risks and what would change the plan

- **The union-branch wording (F1) is rejected.** Then slice 1 becomes a `timeline/v0.8` bump and a migration slice; every
  gate (equivalence, ledger, conformance, snapshots) is re-planned.
- **`details` cannot be carried by one serializer** because #142 lands a competing diagnostic type first. Then slice 0
  adopts that type; the message and keys do not change.
- **The terse bend (F8) is refused.** Then slice 2 adopts an explicit keyword; slices 0, 1, 3 and 4 are unaffected.
- **A committed Project changes verdict in a sweep.** Stop: it means a consumer was missed; amend the design (consumer
  inventory) before continuing.
- **Hypothesis finds a twin or minimality counterexample.** Treat it as a design defect in the date rule (calendar
  sources are the likely cause), not a test to loosen.

## 11. Progress and lead decisions

Lead decisions (2026-10-01), all as the design recommends: L1 #788 stays open until the derived form ships (slice 1 and
the lead's acceptance review); L2 the mode is `scheduled-point`; L3 `constraints.at.max` ships beside `min`; L5 in place,
one L1 delta, one sentence in Spec 56 section 3.2; L6 terse spelling per design 8, after #148 S4; L7 no calendar
snapping; L8 no public example; L9 the "nothing to derive from" check lives in `validate_project` with `E_DERIVATION`.
L4 (`W_DEADLINE`) stays lead-gated.

- Slice 0 (`I788-S0`): implemented as specified. Implementation notes: `Diagnostic.details` is keyword-only with
  `compare=False, hash=False`; the `review` mapping needed no code (it serializes `Diagnostic.as_dict()`, which now
  includes `details` when present); a scheduler-time rejection still returns the placements it computed, as before (the
  design's "return no placements" is about the plan-level rule, which slice 0 does not change).
- Slice 0 merged as #796 (`ab530bb7`).
- Slice 1 (`I788-S1`): implemented as specified, with these corrections to the plan. (1) The repository has no `hypothesis`
  (tests/unit/chrona/terse/test_properties.py says so and `pyproject.toml` lists none): the properties I1 to I4 and "never a
  fixed target" run over a deterministic `random.Random(788)` walk of generated acyclic plans instead (adding a dev
  dependency would edit `pyproject.toml`, which #142 owns). (2) `validate_project` also checks that `constraints.at.min` and
  `max` are real dates (`E_SCHEMA` at `/objects/<id>/schedule`, as for `fixed-span`): the schema checks the shape of a date,
  not the calendar, and the scheduler would otherwise raise `TemporalError` on `2027-02-30`. (3) The ledger test's
  synthetic-property case lists one more path (`schedule.scheduled-point.constraints.at.target`) because it injects a
  property into the shared `bounds` definition. (4) Found, not fixed (outside the slice): `schedule()` raises
  `TemporalError("Latest placement precedes earliest placement")` from the backward pass on some plans that mix calendar-day
  and working-day lags, with no derived point involved (example: two scheduled spans, lags `{1wd in six}`, `4d`, `4wd`); the
  property tests schedule with the analysis pass stubbed out for that reason. (5) Baseline: the schema-equivalence baseline
  gained the 16 probe rows of the new inline Project; the other rows are untouched (a full `--record-baseline` also rewrites
  unrelated rows, so the rows were merged by hand).
- Slice 2 (`I788-S2`): implemented as specified (rules T1 to T6, narrowed `E_TERSE_SCHEDULE_REQUIRED`, N7 in Spec 65, the
  slice 1 ledger entries flipped to `mapped`). Implementation notes: a `calendar CAL` clause may sit between a schedule-less
  gate and its `after` (`g gate calendar std after x`); an `at` bound after a date or after `after`, and `at` on a `task`,
  keep their existing generic errors (`E_TERSE_TOKEN_UNEXPECTED`, `E_TERSE_AMOUNT_INVALID`) with an `at`-specific hint; the
  hints of Core's `E_FIXED_TARGET_VIOLATION` and `E_CONTRADICTORY_BOUNDS` in `usecases/terse_compile.py` now name the derived
  gate and the `at <=` cap. The card replaces its "gates always need a date" rule with the derived-gate spelling and the card
  test pins the placements it states. The skill (`skills/chrona/**`) teaches the YAML mode (`scheduled-point`) only: it
  does not teach terse and a test forbids `chrona compile` in it, so its "never compute a date by hand" rule now says a
  gate that follows its work is declared `scheduled-point` and a `fixed-point` date is for a promised date; a skill test
  runs those claims. The #148 go/no-go re-run with fresh agents (the plan's Proof) is not done here: it needs three fresh
  agents and is recorded on #148 when run.
- Slice 3 (`I792-S1`, #792): implemented per its work record; `L4` is applied (the `schedule` JSON field was decided there, D4/D5,
  with the #142 record shape now that the agent interface has shipped). Slice 4 assessed: `docs/guides/cli-reference.md` is a
  generated flag list (no prose to carry `details` or `warnings`), the skill statements that became stale were corrected in
  slices 2 and 3, and the tutorial (L8: no public example) has no stale statement, so no further teaching change is made.
