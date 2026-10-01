# Design - A gate that is derived from its dependencies (#788)

**Status:** Proposed. Published with its [design plan](../planning/active/issue-788-derived-gate-design-plan-2026-10-01.md),
[architecture review](../reviews/current/issue-788-derived-gate-architecture-review-2026-10-01.md) and
[implementation plan](../planning/active/issue-788-derived-gate-implementation-plan-2026-10-01.md). No product code,
schema, specification or example changes in the pack's PR.
**Base:** `main` at `648c4f9a` (2026-10-01).
**Owner direction:** "even a gate should support a scheduled form." A point whose date is derived is wanted.
**Normative homes after implementation:** Spec 04 (scheduling), Spec 05 (Project format), Spec 56 section 3.2 (schema
evolution), Spec 65 (terse syntax). This file is rationale and the contract the slices implement; it is not a
second specification.

## 1. Decision summary

| # | Decision | Recommendation | Consequence |
| --- | --- | --- | --- |
| D1 | Representation | A new schedule mode `scheduled-point` (section 3). Not `scheduled` with `amount: 0d`. | One new optional union branch in `project-v0.7`; every existing document keeps its verdict and placements. |
| D2 | What the mode carries | `constraints.at.min` (not earlier than) and `constraints.at.max` (not later than). No `amount`, no `anchor`, no stored date. | Same `bounds` shape as `scheduled`; the hard cap reuses `E_CONTRADICTORY_BOUNDS`. |
| D3 | Date rule | Earliest date at or after every incoming relation's `source + lag` (the relation's calendar rule) and the floor. No calendar snapping. A point with nothing to derive from is `E_DERIVATION`, found by `validate`. | A date is the exact answer of the same arithmetic that validates a fixed point today; a derived gate and its fixed-point twin are interchangeable. |
| D4 | "Must not slip past D" | Two expressions with two jobs: `at.max` rejects (hard cap, day one); `deadline` warns and keeps the chart (soft promise, needs `W_DEADLINE`, slice 3). `deadline` stays inert in the scheduler. | The pair "derived gate + deadline" is clean in meaning but its promise half is unimplemented today; it is a separate, lead-gated slice. |
| D5 | Analysis | Derived points join the critical path and float; the latest date honours `at.max`. | A chain that ends in a derived gate shows its real critical path; a slack fixed gate hides it. |
| D6 | Scene, View, Actual, baseline | No change in View, Layout, Scene or adapters. `attachesTo` accepts a `scheduled-point` source. | Verified: a derived gate and its fixed twin render byte-identical SVG. |
| D7 | Slice 0 | `E_FIXED_TARGET_VIOLATION` gains an exact message and an additive `details` object (section 4). | The second branch of the issue's acceptance, on its own, without any schema change. |
| D8 | Terse | `gate after X +2wd` derives; `gate at >= D after X +2wd` adds a floor; `at <= D` a cap. `E_TERSE_SCHEDULE_REQUIRED` is narrowed, not retired. | One construct, one mapping; sequenced after #148 S4. |
| D9 | Schema evolution | In place, no version bump, one declared L1 delta; Spec 56 section 3.2 gets one sentence (section 9). | Precedent: the `end` anchor endpoint widened in place in View v0.28. |

Decisions that need the lead are collected in section 13 with the same numbering plus L-numbers.

## 2. What exists today (evidence)

- **A scheduled object is a span.** `_place_scheduled` returns `{"start", "end"}`; `amount` must match
  `^[1-9]\d*(d|w|wd)$` (schema `scheduledAmount`, `validate_project` `E_INVALID_AMOUNT`). A zero amount is rejected on
  purpose, and `scheduled` objects expose `start` and `end`, never `at` (`_schedule_endpoints` in `core/validation.py`).
- **A fixed object is checked, never placed from dependencies.** `_validate_fixed_targets` computes for each relation
  `required = advance(source endpoint, lag, relation calendar)` and, when the fixed endpoint is earlier, emits
  `E_FIXED_TARGET_VIOLATION` with the fixed message and the pointer `/relations/<id>`. `required` is not reported.
- **The scheduler already has the machinery.** `_lower_bound` folds every incoming relation (and `constraints.*.min`)
  into one lower bound per target endpoint, waits for unplaced sources (so chains and out-of-order objects work), and
  handles the three calendar sources of a lag (the lag's own `calendar`, the target object's, the project's). It is keyed
  by endpoint name, so an `at` endpoint needs no new code to be folded.
- **Presentation never reads the mode.** Rows, marks, deltas, folded points and lanes branch on the placement shape
  (`"at" in planned`). `is_rollup` is the only mode read in `presentation/`.
- **Committed gates are commitments with slack** (design plan section 1): 51 of 55 dependent fixed points in the 37
  committed Projects sit later than their earliest feasible date; 4 sit exactly on it. The owner's rule adds a form; it
  does not describe the existing corpus.
- **`deadline` is inert** (design plan section 1): stored, schema-valid, absent from every consumer; `W_DEADLINE` is
  specified, never emitted.

## 3. Representation (D1, D2)

### 3.1 Options

| Option | What it is | Verdict |
| --- | --- | --- |
| (a) `mode: scheduled`, `amount: 0d`, for gate-type objects only | Relax the positive amount | Rejected. See below. |
| (b) a new mode `scheduled-point` (or `derived-point`) | A fifth union branch whose placement is `{at}` | Recommended. |
| (c1) `fixed-point` with `at` optional | Relax `required: [mode, at]` | Rejected: `fixed` would no longer mean fixed; one mode with two authorities. |
| (c2) a flag on the relation (`derives: true`) | Authority per relation | Rejected: authority is a property of the object (Spec 04 section 3); two relations into one gate would disagree. |
| (c3) a new top-level `derivations` section | Dates computed elsewhere | Rejected: a second place that owns a completed date; the schedule union is already "completed-date authority for one Project object". |

Why (a) fails, concretely:

1. **"Gate-type only" cannot be stated.** The Project `type` is a free label (Spec 65 section 3.2 S3; `milestone`,
   `EVT`, extension types exist in the committed corpus). The schema cannot condition on it, and Core must not make
   scheduling meaning depend on a label that profiles define. Either every type gets `0d` or Core reads a label.
2. **The placement shape would depend on a value.** A zero-length `scheduled` object has `start == end` and would have to
   become `{at}` to be a point (a View treats `{start, end}` as a span, even with zero width). The same mode would
   produce two shapes depending on `amount`, which every consumer would have to know.
3. **Endpoints.** A relation into a point targets `at`; into a `scheduled` object it targets `start`/`end`.
4. **It changes a shared definition.** `scheduledAmount` would stop being "positive", weakening `E_INVALID_AMOUNT` for
   every task, a behavior change to an existing rule rather than an addition.
5. **It carries `anchor`.** An anchored zero-length object is a fixed point by another name.

(b) leaves every existing definition untouched and gives the new form its own, smaller, set of properties.

### 3.2 Name

Modes are named for the **completed-date authority** (the schema's own description of `schedule`): `fixed-point`,
`fixed-span`, `scheduled` (the scheduler is the authority), `rollup` (the children are). A point whose date the scheduler
owns is `scheduled-point`: it pairs with `scheduled`, matches the owner's phrase ("a scheduled form"), and states the
authority. `derived-point` is the alternative (the issue's wording, and Spec 04 section 2.2 already calls a rollup
"derived"); it would be easy to confuse with `rollup`, which is Spec 04's "Derived" placement. The name is cheap to change
before slice 1 and costly after. Lead decision L2.

### 3.3 What the mode carries (D2)

```yaml
schedule:
  mode: scheduled-point            # required; the only required property
  constraints:                     # optional
    at:
      min: 2027-05-07              # not earlier than (the floor)
      max: 2027-06-30              # not later than (the hard cap)
```

- No `amount` (a point has no duration), no `anchor` (an anchored date is a `fixed-point`), no stored date.
- `constraints.at` is the existing `bounds` definition (`min`, `max`, both optional, both ISO dates). The `constraints`
  object for a point is its own definition (`at` only), so a `scheduled` span still cannot carry `at` and a point
  cannot carry `start` or `end`.
- `min` is the issue's "optional not-earlier-than bound". `max` is not in the issue; it is included because it costs no
  new shape (the same `bounds`), it is what the fixed point gave authors ("rejected when dependencies push past it") and
  without it the derived form has no hard commitment at all (section 6). Lead decision L3.

### 3.4 Schema text (what slice 1 adds)

```yaml
# $defs/schedule/oneOf gains a fifth branch
- {description: "Single date derived from the object's dependencies and optional bounds.", $ref: "#/$defs/scheduledPoint"}
# $defs/schedule/examples gains
- {mode: scheduled-point, constraints: {at: {min: "2026-10-01"}}}
# new definitions
scheduledPoint:
  type: object
  description: "Point whose completed date is derived from its dependencies and optional bounds; it stores no date."
  additionalProperties: false
  required: [mode]
  properties:
    mode: {description: "Selects the dependency-derived single-date form.", const: scheduled-point}
    constraints:
      type: object
      description: "Optional bounds on the derived date."
      additionalProperties: false
      properties:
        at: {description: "Not-earlier-than (min) and not-later-than (max) bounds for the derived date.", $ref: "#/$defs/bounds"}
```

Descriptions and the example are required by the schema-annotation lint (Spec 56 section 2). No shared part is touched
(`bounds` is a local definition; the `at` endpoint is already in the `dateEndpoint` vocabulary part).

### 3.5 Schema evolution

In place under Spec 56 section 3.2; see section 9 for the argument, the gate output and the one sentence the specification
needs.

## 4. Slice 0: the better rejection (D7)

### 4.1 Rule

`E_FIXED_TARGET_VIOLATION` keeps its code, count (one per violating relation) and pointer. It gains a deterministic
message and an optional `details` object. For each violating relation the scheduler already has `required`; slice 0 adds
the maximum over **all** relations into the same target endpoint (`earliest`) and the relation that gives it
(`forcedBy`; first in relation order on a tie).

### 4.2 Message

One template, no free text:

```text
{object}.{endpoint} is fixed at {placed}, but relation {relation} ({from.object}.{from.endpoint} {from.value} {sign} {lag}) requires {required} or later. The earliest feasible date for {object}.{endpoint} is {earliest} (forced by {forcedBy}).
```

- `{relation}` is the relation `id`, or `/relations/N` (zero-based index) when it has none.
- `{sign} {lag}` renders `+ 2wd`, `+ 0d`, `- 2d`; a calendar-qualified lag renders `+ 2wd in six`.
- Example for the committed shape of the issue (gate at 2027-05-17, QA ends 2027-05-14, `+2wd`):

```text
launch.at is fixed at 2027-05-17, but relation qa-launch (qa.end 2027-05-14 + 2wd) requires 2027-05-18 or later. The earliest feasible date for launch.at is 2027-05-18 (forced by qa-launch).
```

### 4.3 Fields

```json
{"code": "E_FIXED_TARGET_VIOLATION", "severity": "error", "component": "core",
 "sourceRef": "/relations/qa-launch", "revisionRefs": [],
 "message": "launch.at is fixed at 2027-05-17, but relation qa-launch (...) ...",
 "details": {"object": "launch", "endpoint": "at", "placed": "2027-05-17",
             "relation": "qa-launch", "from": {"object": "qa", "endpoint": "end", "value": "2027-05-14"},
             "lag": "2wd", "required": "2027-05-18",
             "earliest": "2027-05-18", "forcedBy": "qa-launch"}}
```

- `details` is optional and additive to the diagnostic shape (Spec 65 section 6.1 already extends the shape additively
  with `source`, `sourceRange`, `hint`). Only diagnostics that have details carry the key. Keys listed above are the
  stable contract for this code; keys may be added, never renamed.
- Dates are ISO strings. `lag` is the Project value verbatim (string, or `{value, calendar}`).
- `details` is a field of the Core `Diagnostic` (single owner), serialized by one helper that every surface uses
  (`chrona schedule`, `chrona render`, the terse draft ingress, and the #142 agent interface). It must not be added to
  one serializer only.
- For a fixed span the answer is per endpoint (`build.start`); moving a span's start alone changes its length, so the
  message does not claim a full re-placement. For a `fixed-point` it is the whole answer, which is the case of the issue.
- The pointer for a relation **without an id** is today `/relations/<target object id>`, a pointer that does not exist
  in the Project. Slice 0 changes only that fallback to `/relations/N` (the index, as `validate_project` already uses).
  Pointers for relations with an id do not change (Spec 65 section 6.4 maps both spellings).

### 4.4 Acceptance test (the issue's literal line)

A fixed-point gate behind a duration task, the case of the issue: build fixed-span `2027-04-26..2027-05-07`, `qa`
scheduled `5wd` after build, `launch` fixed-point `2027-05-17` and a `2wd` relation from `qa.end`. The test asserts the
code, the pointer, the exact message, every `details` key, that substituting `earliest` for `at` makes `schedule` accept
the plan, and that one day earlier is rejected again (the author can correct the date in one step). A second case has two
violating relations of different strength and asserts `earliest` and `forcedBy` on both diagnostics.

### 4.5 What slice 0 must not do

Change which plans are rejected, the number of diagnostics, a code, or any pointer except the id-less fallback; return
placements for a rejected plan; propose or apply a correction; add a hint that promises a feature that does not exist yet
(for example "make it a scheduled-point"); touch `E_CONTRADICTORY_BOUNDS` of existing code paths.

## 5. Semantics of the derived date (D3, D5)

### 5.1 The rule

For an object `P` with `schedule.mode: scheduled-point`:

```text
bounds(P) = { advance(value(r.from), lag(r), calendar(r)) : r a relation with r.to = (P, at) }
            + { constraints.at.min }                        (when present)
date(P)   = max(bounds(P))
```

`calendar(r)` is exactly the rule `_lower_bound` and `_validate_fixed_targets` use: the lag's own `calendar`, else the
object's `calendar`, else the project's; only a lag with a `wd` part uses one. `date(P)` is placed as `{at: date(P)}`.
If `constraints.at.max` is present and `date(P)` is later, the schedule fails with `E_CONTRADICTORY_BOUNDS`
(`/objects/<id>/schedule/constraints/at/max`), the code and message already used for a `scheduled` span's `end.max`;
the placement is still returned in the result, as for spans.

Properties this gives, each a proof obligation in section 11:

- **I1 (twin).** Replacing every derived point by a `fixed-point` at its derived date yields a plan that `schedule`
  accepts with identical placements.
- **I2 (minimal).** When no floor is binding, a `fixed-point` one day earlier is rejected with
  `E_FIXED_TARGET_VIOLATION`, and slice 0's `earliest` equals the derived date.
- **I3 (monotone).** Making a predecessor later never makes a derived point earlier.
- **I4 (order-free).** Placement does not depend on object or relation order (Spec 04 section 19).

### 5.2 No calendar snapping

The derived date is not moved to a working day. Spec 04 section 21 normalizes the candidate **start of a scheduled span**
on a working calendar; a point has no amount, and "a fixed endpoint is never normalized". Snapping would also break I1
and I2 (the fixed twin could not sit on a non-working day the derived date had skipped). The visible consequence, spiked:
a `+2d` relation from a Friday lands on a Sunday. An author who wants working days writes `wd` in the lag, which counts
working dates by construction. A later optional `snap` property would be additive; leaving it out now is the reversible
choice. Lead decision L7.

### 5.3 Failure cases

| Situation | Result |
| --- | --- |
| No relation into `at` and no `min` | `E_DERIVATION` "Scheduled point has no predecessor and no minimum date" at `/objects/<id>/schedule`. Emitted by `validate_project` (static: a count of relations and a property), so `validate` and `schedule` agree; this avoids repeating the `validate`/`schedule` split of #780. |
| Cycle through derived points | Found by `schedule`, not `validate`: `E_UNSUPPORTED_CYCLE`, or `E_UNSATISFIABLE_DEPENDENCIES` for a positive calendar-day cycle (spiked: `g1 <-> g2` with zero lag and with `1d`). Same codes and pointers as for spans. Cycle detection in `validate` is #780's, not duplicated here. |
| A derived gate inside a group depends on the group's end | `E_UNSUPPORTED_CYCLE` (spiked): the rollup waits for its children and the child waits for the rollup. A dependency on a sibling task works. |
| `at.max` earlier than the derived date | `E_CONTRADICTORY_BOUNDS` at `.../constraints/at/max`, with `details` `{object, endpoint, derived, max, forcedBy}` (new code path only). `min > max` is the same diagnostic, since `date >= min`. |
| A relation into or out of a `scheduled-point` naming `start` or `end` | `E_ENDPOINT_MODE_MISMATCH` (`_schedule_endpoints` returns `{at}` for the new mode). |
| `attachesTo` host is a `scheduled-point` | `E_PROJECT_ATTACH_TARGET_NOT_SPAN` (a point is not a span). A `scheduled-point` **source** is allowed (section 7). |
| Floor equals a dependency bound | The floor "wins" a tie silently; no driving relation is lost (a tie is not a violation). |
| `min` after `max`, same object | Not a schema error (the schema does not compare dates); reported as above when the date is computed. |

### 5.4 Analysis: critical path, float, driving relations

`_analyze_criticality` already treats a non-fixed object with an `at` placement (`_latest_at_target` and
`_cap_latest_endpoint` have an `at` branch that no object reaches today). Slice 1 verifies this with tests and makes one
change: `_latest_at_target` must return `min(target, constraints.at.max)` for a point, as it does for a span's `end.max`.
The driving-relation test (`source + lag == target.at`) needs no change; a binding floor leaves no driving relation.

Spiked consequence, because it is the point of the owner's rule and a behavior change authors will see: with a derived
gate that ends a chain, the critical set is `{a, c, g}` and the short branch `b` has float 5; the same plan with a slack
fixed gate at 2027-06-30 reports critical `{a, g}`, `b` float 35 and `c` float 30. A slack fixed gate dwarfs the chain, so
total float stops describing the plan. A derived gate restores it. This is a feature, and a reason for the corpus to
adopt the form deliberately rather than automatically.

## 6. Commitment beside derivation (D4)

### 6.1 The tension

Today `fixed-point` is two things at once: a date and a committed target (the plan is rejected when dependencies push
past it). The owner's rule removes the stored date, so the commitment must live elsewhere or not exist. A derived gate
that always satisfies its dependencies by moving cannot say "no later than".

### 6.2 What exists

| Tool | Reads | Effect today | Where defined |
| --- | --- | --- | --- |
| `fixed-point` plus a dependency | the date | rejects (`E_FIXED_TARGET_VIOLATION`) when dependencies need a later date | Spec 04 section 15.1 |
| `constraints.end.max` on a `scheduled` span | the date | rejects (`E_CONTRADICTORY_BOUNDS`) when the span ends later | Spec 04 section 9 |
| `deadline` on any object | nothing | none: stored, never read | Spec 04 section 10; Spec 05 section 9; Q-SCHED-2 |

Facts that matter for the pair "derived gate plus deadline":

- `deadline` has **no consumer** anywhere: not the scheduler, not validation, not View, Layout, Scene or an adapter.
  `grep deadline src schemas` finds the terse ledger entry and the schema. The committed corpus uses it 11 times (10 on
  fixed points, 1 on a span), always on or after the planned date: the corpus already uses "planned date plus promise",
  with the planned date written by hand and the promise never evaluated.
- `W_DEADLINE` is a documented identifier ("Resolved schedule violates a deadline", core-v0.1-diagnostics) and Spec 04
  section 23 lists "deadline diagnostics" in the conformance subset a scheduler MUST support. The reference scheduler
  does not emit it. This is a gap between specification and code that predates #788 (review F6).
- A rejected plan returns no placements and `render` refuses it, so a **hard** cap means a slipping project can no
  longer be drawn. That is the strongest argument for a soft form.

### 6.3 The pair, and what each half is for

| Intent | Expression | Behavior | Available |
| --- | --- | --- | --- |
| "The launch is 2 working days after QA" | `scheduled-point` | date computed | slice 1 |
| "...but not before 2027-05-07" | `constraints.at.min` | date is at least the floor | slice 1 |
| "...and if it would slip past 2027-06-30, the plan is invalid" | `constraints.at.max` | `E_CONTRADICTORY_BOUNDS`; plan rejected | slice 1 |
| "...and show me when it slips past 2027-06-30" | `deadline: 2027-06-30` | `W_DEADLINE` warning; plan and chart still produced | slice 3 (needs the gaps below) |

Recommendation: ship the hard cap with the form (it is free and replaces the rejection fixed points gave), document
`deadline` as the default expression of a promise once slice 3 exists, and keep `deadline` inert in the scheduler
(Q-SCHED-2). "Derived gate plus deadline" is therefore a clean pair in meaning (forecast computed, promise stored) and
`deadline` is already stored on the gate today; what is missing is only the evaluation and its surface:

1. **The evaluation.** `deadline_warnings(project, placements)`: for each object with a `deadline`, compare the
   planned finish (`at` for a point, `end` for a span) with it; strictly later is a violation, equal is not. A pure
   function in Core next to `attachment_warnings`, whose precedent (#486) is exactly this shape.
2. **A warning channel.** `ScheduleResult.diagnostics` are all errors: `ok` is "no diagnostics", `analysis` is skipped
   when any exists and the CLI rejects on any. Warnings travel separately today (`attachment_warnings` through
   `usecases/warning_ledger.py` to stderr JSON for `render`). `W_DEADLINE` joins that ledger for `render`; surfacing it in
   `chrona schedule` JSON is an additive result field owned by the agent-interface design (#142) and must be agreed
   with it, not decided here.
3. **A View concept.** There is no deadline mark, role or vocabulary entry, so a chart cannot show "planned
   2027-07-02, deadline 2027-06-30". That is a View and Layout design in its own right and a successor issue; slice 3 is
   the warning only.
4. **Documentation.** `deadline` is `yaml-only` in the terse ledger ("does not affect dates") and stays so.

### 6.4 Corpus note

No committed Project would warn under `W_DEADLINE` (every deadline is on or after its planned date), so slice 3 changes no
verdict and no byte of public output (the warning is stderr; the SVG is unchanged).

## 7. Scene, View, Actual, baseline, scenario, attachment (D6)

The View, Layout, Scene and adapters read placements. A `scheduled-point` produces `{at: date}`, which every consumer
already handles for `fixed-point`. Spiked: a three-object plan with a derived gate and an Actual `{at: 2027-05-21}`
rendered through the draft path, and its fixed-point twin (`at: 2027-05-18`) rendered to **byte-identical SVG**.

| Surface | Behavior with a derived gate | Change needed |
| --- | --- | --- |
| Planned mark, table cell, ordering | The derived date, as for a fixed point | none |
| As-of and `missingActual` | Due when the derived `at` is on or before `asOf` (Spec 06 section 8.4) | none |
| Actual `{at}` and the `+Nd` label | `at_delta = actual.at - planned.at` in calendar days (Spec 06 section 8, `ReviewItem.at_delta`) | none |
| Actual and rescheduling | **Unchanged**: Actuals never move the planned date (Spec 04 section 17; Spec 06 section 8.2). The derived date is a *derived plan*, not a forecast from reality. A late predecessor Actual does not move the gate | none; state it in Spec 04 (slice 1) so "derived" is not read as "forecast" |
| Baseline (snapshot) compare | The snapshot is scheduled by the same function, so a gate that moves between baseline and current shows as a planned-versus-baseline delta; a fixed gate cannot move (it rejects) | none |
| Scenario | A scenario that adds or removes a dependency or replaces an object's schedule is scheduled by the same function; a derived gate moves inside the scenario where a fixed gate would reject it | none (unverified end to end; slice 1 adds one scenario test) |
| Attached milestones (#486, #517, #518) | `attachesTo` currently requires the source's mode to be `fixed-point` (`core/attachments.py`) | allow `scheduled-point` as a source; the host test (`E_PROJECT_ATTACH_TARGET_NOT_SPAN`) also treats a `scheduled-point` as a point. `W_PROJECT_ATTACHED_OUTSIDE_HOST` is computed from placements and works (spiked) |
| Critical role | A gate may now carry `critical` (section 5.4) | none; visible only in plans that adopt the form |
| Folded points, lanes, member labels | Key on `at` and `attached_to` | none |
| Table and plot row ordering | Uses `planned.at` | none |

**Public slides and corpus examples that change: none.** No committed Project can use the mode (it does not exist
yet) and none is edited. The only committed derived documents that change are regenerated by the main sync and not by
any slice: `docs/examples/corpus-coverage.md` (one new uncovered row for `objects.*.schedule.mode`),
`docs/diagnostics/inventory.md` (source locations of `E_FIXED_TARGET_VIOLATION` and any new diagnostic move).
`docs/diagnostics/declared-value-inventory.md`, `docs/diagnostics/vocabulary-inventory.md` and
`docs/gallery/presentation-coverage.md` do not mention schedule modes (grepped) and do not change.
Whether a public example should teach the form is a separate lead decision (L8; recommendation: not in this issue).

## 8. Terse syntax (D8)

### 8.1 Grammar delta (Spec 65)

```text
schedule    = DATE | DATE ".." DATE | AMOUNT [ anchor ] { bound } | pointbound { pointbound } | (nothing, for a gate) ;
pointbound  = "at" ( ">=" | "<=" ) DATE ;               (each at most once; "at" is already a reserved word)
object      = NAME [ STRING ] KIND [ schedule ] [ "calendar" CAL ] [ after ] ;     (unchanged)
```

| Rule | Text |
| --- | --- |
| T1 | A `gate` with no schedule words and an `after` clause compiles to `{mode: scheduled-point}`: `launch "Launch" gate after qa +2wd`. |
| T2 | `at >= D` is `constraints.at.min`; `at <= D` is `constraints.at.max`. They sit in the schedule slot, before `calendar` and `after`, and require an `after` clause: `launch "Launch" gate at >= 2027-05-07 after qa +2wd`. |
| T3 | `E_TERSE_SCHEDULE_REQUIRED` is **narrowed, not retired**: a `task` with no schedule (unchanged hint); a `gate` with neither a date nor `after` (message: a gate needs a date, or `after X` to derive one); a `gate` with bounds but no `after` (a floor alone is a spelling of a fixed date: write `gate DATE`). |
| T4 | A `task` with no schedule and an `after` clause remains `E_TERSE_SCHEDULE_REQUIRED`: there is no derived span (section 12). |
| T5 | Default endpoints: `after launch` where `launch` is derived is `launch.at`; the dependent derived gate's relation targets `at`. `.start` or `.end` on it is Core's `E_ENDPOINT_MODE_MISMATCH`, as for a fixed point. |
| T6 | Source map: `/objects/NAME/schedule` maps to the kind word for the implicit form (the precedent: `rollup` maps to its kind word) and to the bound clause when bounds exist; `.../constraints/at/min` and `.../max` to their clauses. |

### 8.2 Why not the sketch `gate after qa +2wd >= 2027-05-07`

A trailing `>= D` after a comma list is ambiguous: in `after a +1d, b >= D` the date could bind to `b`'s lag or to the
object. It also omits the endpoint the bound constrains (the grammar's other bounds name `start` or `end`). `at >= D`
mirrors `start >= D`, reuses a reserved word, keeps one slot for everything schedule-shaped and reads as English ("gate at
or after 2027-05-07, after qa plus two working days").

### 8.3 The one bend

Spec 65 S3 says the kind does not constrain the form. T1 is the first place the kind selects it: `gate` is the point
kind of the grammar, `task` the span kind. That is the same character as normalisation N1 (a deliberate, documented bend);
it is recorded as normalisation N7 and in the review (F8). The alternative, a keyword in the schedule slot, is
kind-neutral but adds a token to the very case the issue wants shorter.

### 8.4 Scope rule and the ledger

Section 1.1's scope rule holds: it determines a date, is scalar, has one spelling. The ledger test walks the live schema
and fails until the new paths are classified, so slice 1 lands them as `yaml-only` ("a derived point is not spellable
yet") and slice 2 flips them to `mapped`. Slice 2 is sequenced **after #148 S4** (it edits Spec 65, the terse guide,
parser, compiler, ledger, and the guide's error table, which S4 also edits). The #148 go/no-go finding that "a gate with
both a fixed date and `after` acts as a floor" is, precisely, validation: the date is authoritative and the dependency is
checked against it. The real floor is `at >=`, new here.

## 9. Schema evolution (D9) and the S0 gate

Spec 56 section 3.2 says an additive **optional property** is added in place when omitting it preserves prior behavior,
and reserves a bump for a change that makes an existing resource invalid or changes its behavior. A new union branch is
not a property, so the rule does not name it. Its intent is satisfied: no existing document changes verdict or
placement, and a document that does not use the branch is read exactly as before. The repository already did the same
once: View v0.28 widened the annotation anchor `endpoint` enum with `end` in place, recorded as an L1 delta ("a widening:
every existing document stays valid and renders the same").

The mechanical bump rule is not engaged (it fails a *bump* that is only additive properties; this is not a bump).
Recommendation: in place, and one sentence added to section 3.2: "adding a tagged branch to an existing discriminated union
is a widening, treated like an optional property: in place, with one L1 delta entry, when no existing document's verdict
or behavior changes." Lead decision L5. A bump to `timeline/v0.8` would leave every document valid but force a migration of
every pinned `version: timeline/v0.7` (37 committed Projects, every snapshot) and is not justified by a widening.

**S0 gate output** (`python -m tools.schema_equivalence --base-rev origin/main`, run locally on a spike of the branch
in section 3.4; working tree restored afterwards):

```text
L1 structural (base origin/main): changed=1, equal=40
  changed   project-v0.7.schema.yaml /properties/objects/additionalProperties/properties/schedule/oneOf [4 branches] -> [5 branches]
L2 corpus: 365 tracked documents, 267 mapped, 4 invalid (the 4 expected-invalid), 98 unmapped, 0 unparseable
L3 diagnostics: 723 probes (448 rejected, 275 accepted), 4 invalid documents
FAIL L1 project-v0.7.schema.yaml: .../schedule/oneOf   (until the delta below is listed)
```

Reading it: L1 has exactly one difference, in the one place the change was made, and the gate fails closed until the
delta is declared (a union branch is neither "equal" nor the property-insertion the gate classifies as "additive"). L2 and
L3 report no verdict or diagnostic change on any committed document or probe. Slice 1 adds one entry to
`conformance/schema-equivalence/expected-deltas-v0.1.yaml` (`before` the four dereferenced branches, `after` the five,
reason "widening: every existing document stays valid", test the golden cases of section 11.2) and two L3 probe sites for
the new date sites (`constraints.at.min` and `.max`) on an inline base document, recorded in the baseline without changing
any existing row. After that the gate prints `delta` for the schema and passes.

## 10. Consumer inventory: what each must do

| Consumer | Today | Must do | Slice |
| --- | --- | --- | --- |
| `schemas/project-v0.7.schema.yaml` | four branches | add `scheduledPoint`, example, descriptions | 1 |
| `tools/schema_annotations.py` lint | every author-facing node has a description; a branch an example | satisfied by 3.4 | 1 |
| `tools/schema_equivalence.py`, `conformance/schema-equivalence/*` | L1 fingerprint, L2 corpus, L3 probes | one L1 delta; two probes | 1 |
| `core/validation.py` | `_schedule_endpoints`: `fixed-point` -> `{at}`, else `{start,end}`; per-mode checks | `scheduled-point` -> `{at}`; static `E_DERIVATION` check | 1 |
| `core/attachments.py` | source must be `fixed-point`; host must not be `fixed-point` | source may be either point mode; host rejects either point mode | 1 |
| `scheduling/scheduler.py` | fixed first, then `scheduled` and `rollup`; unknown mode -> `E_ROLLUP_SCHEDULE` | a `scheduled-point` branch; `_latest_at_target` honours `at.max`; slice 0 details | 0, 1 |
| `core/diagnostics.py`, `app/cli.py` (`_diagnostic`, `_reject`), `terse/diagnostics.py` | `Diagnostic(id, message, path)`; `TerseDiagnostic` builds its own dict and is constructed positionally | optional keyword-only `details`; one shared serializer; terse passes it through | 0 |
| `usecases/project_checks.py`, `usecases/draft_render.py`, #142 interface | carry `Diagnostic` objects | no logic; they inherit `details` (check the #142 result shape) | 0 |
| `presentation/*` (View, Layout, Scene, renderer) | placements only; `is_rollup` reads the mode | none | - |
| `presentation/model/authoring.py` (guided workspace) | emits only `fixed-span` | none (guided source has no gate form) | - |
| `terse/parser.py`, `compiler.py`, `ledger.py`, Spec 65, `docs/guides/terse-plan.md` | gate needs a date | section 8 | 2 |
| `conformance/conformance-v0.1.yaml`, `tests/integration/test_conformance.py` | authority cases for fixed and scheduled | derived-point cases | 1 |
| Spec 04 (2.1, 2.3, 4, 15.1, 20, 23), 05, 56 (3.2), `supplemental/core-v0.1-diagnostics.md` | no point derivation | state the form and rule; `details` on the code | 0, 1 |
| `skills/chrona/SKILL.md`, `references/authoring-model.md`, `references/diagnostics.md` | modes listed without the new one; `E_FIXED_TARGET_VIOLATION` remedy "move the date later" | teach the form and the new detail (another PR edits `diagnostics.md`: rebase) | 4 |
| `docs/examples/corpus-coverage.md`, `docs/diagnostics/inventory.md` | derived | regenerated by main sync; never edited | - |
| `tests/unit/chrona/terse/test_ledger.py` | walks the live schema; fails on an unclassified path | classify new paths | 1, 2 |
| Federation exports | display-only copy of `schedule` | none | - |
| Scenario resolution | overlays and re-schedules | none; one test | 1 |

## 11. Proof plan

### 11.1 Equivalence on what exists

- **Scheduler equivalence on every committed Project.** Before and after each code slice, `schedule()` is run on all 37
  committed `timeline/v0.7` Projects (and their scenarios and snapshots); the (placements, diagnostics, analysis) triples
  are compared as canonical JSON. Expected: identical for every Project (none uses the mode). Slice 0 is allowed one
  difference class only: the new message and `details` of `E_FIXED_TARGET_VIOLATION`, on plans that already rejected. A
  sweep marked `corpus` ships with its synthetic twin (AGENTS.md), and the sweep result is pasted in each PR.
- `python tools/regenerate_public_examples.py --check --jobs 4` (byte-identical public output) and
  `python conformance/run_conformance.py`.
- The S0 schema-equivalence run (section 9) is pasted in the slice 1 PR, with the delta listed and `L1 ... delta`.

### 11.2 Golden scheduling cases (slice 1)

Calendar `std` is mon-fri with one exception, 2027-05-03 off; `six` is mon-sat. Dates below are the spiked values.

| Case | Setup | Expected |
| --- | --- | --- |
| G1 gate behind a duration task | `build` fixed-span 2027-04-26..2027-05-07; `qa` scheduled 5wd after `build.end`; `launch` derived, `qa.end + 2wd` | `qa` 05-07..05-14; `launch.at` 2027-05-18. Fixed twin at 05-18 accepted; at 05-17 rejected with `earliest` 05-18 |
| G2 two predecessors | `a.end` 05-10 `+1d`; `b.end` 05-14 `+0d` | `at` 2027-05-14; the driving relation is `b`'s |
| G3 lag on another calendar | `a.end` 05-07 (Fri), lag `3wd`; then the same with `{value: 3wd, calendar: six}` | 2027-05-12 on `std`; 2027-05-11 on `six` (Saturday works) |
| G4 floors | floor 05-21 vs bound 05-12; floor 05-08 vs 05-12; floor only; neither | 05-21 with no driving relation; 05-12; 05-21; `E_DERIVATION` |
| G5 chained derived gates | `a.end` 05-07; `g1` `+1wd`; task `t` 3wd after `g1.at`; `g2` `t.end + 1d` | `g1` 05-10; `t` 05-10..05-13; `g2` 05-14 |
| G6 cycles | `g1 <-> g2`, zero lag; positive lag | `E_UNSUPPORTED_CYCLE` on both; `E_UNSATISFIABLE_DEPENDENCIES` on both |
| G7 cap | derived 05-12, `at.max` 05-10 | `E_CONTRADICTORY_BOUNDS` at `/objects/g/schedule/constraints/at/max` |
| G8 analysis | `a`, `b` 3wd, `c` 8wd, gate after `b` and `c` | critical `{a, c, g}`, `b` float 5; the slack fixed twin at 06-30 gives `{a, g}`, `b` 35, `c` 30 |
| G9 wrong endpoint | relation `to.endpoint: start` onto a derived gate | `E_ENDPOINT_MODE_MISMATCH` at `/relations/0/to/endpoint` |
| G10 group | gate child of a group that depends on the group's end; and on a sibling | `E_UNSUPPORTED_CYCLE`; placed (gate `at` 05-08 for a sibling ending 05-07 with `+1d`) |
| G11 attach | derived point attached to a host, dated after the host's end | accepted; `W_PROJECT_ATTACHED_OUTSIDE_HOST` |
| G12 calendar-day lag | `+2d` from a Friday | a Sunday (no snapping), accepted |

### 11.3 Property tests (Hypothesis is already a dev dependency)

Over generated acyclic plans with spans, lags (`d`, `w`, `wd`, own calendar), floors and derived points: I1 (twin
substitution accepts with identical placements), I2 (one day earlier rejected, `earliest` equals the derived date, when
no floor binds), I3 (monotone in every predecessor), I4 (placements identical under permutation of objects and
relations), and "no `scheduled-point` plan is ever rejected for a fixed-target reason" (derived points are never fixed
targets).

### 11.4 Diagnostics

Exact-text fixtures for the slice 0 message (including the id-less relation, a negative lag, a calendar-qualified lag,
a `fixed-span` target, two relations of different strength); a CLI test of the JSON shape with and without `details`; the
existing `test_chrona_skill_diagnostics` case `fixed-target` stays green.

## 12. Non-goals

- **A derived `fixed-span`.** Out of scope and proposed only as a non-goal: a span with no `amount` whose both ends are
  derived makes duration an output, which Spec 04 section 3 warns against (a span must not treat start, end and amount as
  independent authorities), and it changes float computation (which needs the amount). Nothing in the evidence needs it;
  `rollup` already derives a span from children and `scheduled` derives one from an amount.
- Converting any committed gate, and any automatic migration of a fixed gate to a derived one (section 6: 51 of 55 are
  commitments with slack; conversion would move dates or silently drop the slack).
- Rescheduling from Actuals or a forecast (Spec 04 section 17; deferred policy).
- A deadline mark, role or Scene element (section 6.3, item 3).
- Calendar snapping of the derived date (L7), a `point` object kind, any extension-defined schedule form.
- Reading the Project `type`: `scheduled-point` works for any label (`gate`, `milestone`, `EVT`).

## 13. Decisions for the lead

| # | Decision | Recommendation | If declined |
| --- | --- | --- | --- |
| L1 | May #788 close after slice 0 (the issue's literal "or") or only after the derived form (slice 1, and 2)? | Keep it open until slice 1 ships; the owner's direction is the derived form. Slice 0 satisfies the second branch of the acceptance and is published first. | Close on slice 0's acceptance review; open a successor for slices 1 to 4. |
| L2 | Mode name | `scheduled-point` | `derived-point`; same design, rename in the schema text and Spec 04. |
| L3 | Include `constraints.at.max` (hard cap) beside `min` | Yes | `min` only; the hard commitment then has no expression until `deadline` warns (slice 3). |
| L4 | Build `W_DEADLINE` (slice 3), and where it surfaces in `chrona schedule` JSON | Yes, `render` warning first; the `schedule` JSON field agreed with #142 | Leave `deadline` inert; `at.max` is the only enforced promise and a slipping plan cannot be drawn. |
| L5 | Schema evolution | In place, one L1 delta, one sentence in Spec 56 section 3.2 | `timeline/v0.8` bump: every pinned document migrates. |
| L6 | Terse spelling | Implicit `gate after X`; `at >= D`, `at <= D` in the schedule slot; sequenced after #148 S4 | An explicit keyword (kind-neutral, longer); or defer the terse form and keep slice 0 plus 1. |
| L7 | Calendar snapping | None now; a later optional `snap` property is additive | Snap to the object's calendar: breaks the twin and minimality invariants (I1, I2). |
| L8 | Teach the form in a public example or onboarding step | No: keep the corpus byte-stable; the skill and guides carry the teaching (slice 4) | Add one onboarding step in its own PR, with its generated evidence. |
| L9 | Where the "nothing to derive from" check lives and its code | `validate_project`, reusing `E_DERIVATION` (no new code) | A new code, or a scheduler-only check (reintroduces the #780 split). |
