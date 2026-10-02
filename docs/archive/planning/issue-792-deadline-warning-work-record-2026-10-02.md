# Work Record - `deadline` is read and `W_DEADLINE` is emitted (#792, slice 3 of #788)

**Status:** Proposed. One concise living record for the AGENTS.md sequence (baseline, design plan, design, architecture
review, implementation plan). It narrows slice 3 of the
[#788 implementation plan](issue-788-derived-gate-implementation-plan-2026-10-01.md) (section 5) and its
[design](../../design/issue-788-derived-gate-design-2026-10-01.md) (section 6.3), whose L4 decision it applies.
**Base:** `main` at `32a5fb4b`. Every PR is `Refs #788` or `Refs #792`, with no closing keyword.

## 1. Baseline (verified on `main`)

- `deadline` is a Project schema property on every object (`schemas/project-v0.7.schema.yaml`, a `date`), specified by
  Spec 04 section 10 ("a deadline expresses a target against which a resolved schedule can be evaluated"; "may produce
  derived state or a diagnostic"), Spec 05 section 9, Spec 01 section 15 and Q-SCHED-2. Eleven committed values.
- No Core, scheduler, use case, adapter, View, Layout or Scene code reads it. `W_DEADLINE` is listed in
  `core-v0.1-diagnostics.md`, and Spec 04 section 23 requires "deadline diagnostics" of a conforming scheduler; nothing
  emits it. The skill, `mermaid-or-chrona.md` and `authoring-model.md` tell an author that chrona gives no diagnostic.
- Warnings that reach a user today: `attachment_warnings` (a pure Core function over placements) through
  `usecases/warning_ledger.py` to the `render` stderr JSON and to the MCP `render_draft` `warnings` field.
  `ScheduleResult.diagnostics` are all errors (`ok` is "no diagnostics", analysis is skipped when any exists), and
  `chrona schedule` prints `{placements, diagnostics: [], analysis}`; MCP `schedule_project` prints `placements`,
  `analysis` and `diagnostics: []` (Spec 66 section 3: `diagnostics` is empty when `status` is `ok`; warnings are `warnings`).
- `Diagnostic.details` exists (slice 0, #796). The agent interface (#142) has shipped; it fixed the MCP warning record.
- Terse: no `deadline` spelling. `terse/ledger.py` classifies `object.deadline` as `yaml-only` ("does not affect dates").

## 2. Literal acceptance (#792)

- [ ] `W_DEADLINE` is emitted for an object placed after its `deadline` (a test with a fixed-span task and a derived
  gate), or the spec states it is not, and the conformance subset is consistent with whichever.

Related text of the issue: three missing pieces (the evaluation, a warning channel, a View concept) and the decision
"build `W_DEADLINE` (the `render` warning first, then the `schedule` JSON field agreed with #142, then the View mark as
its own issue), or amend Spec 04 section 23".

## 3. Decisions (owner-level judgement calls, recorded on #792)

| # | Decision | Options | Choice and reason | Reverse |
| --- | --- | --- | --- | --- |
| D1 | Where the check lives | (a) `ScheduleResult.warnings`; (b) a pure Core function over placements | (b), `core/deadlines.py::deadline_warnings`, precedent `attachment_warnings`. The scheduler never reads `deadline` (Q-SCHED-2 holds by construction: a test shows a violated deadline changes no placement, verdict or analysis). (a) would widen the `ScheduleOutcome` port and every scheduler double. | Add a field to `ScheduleResult` and call the function from `schedule()`. |
| D2 | The rule | finish = `at` / `end`; strict or non-strict | A point's finish is `at`, a span's (scheduled, fixed or rollup) is `end`, the same stored value `constraints.end.max` compares (Spec 04 section 9). Strictly later is a violation; equal is not. Only planned placements; an Actual never counts (Spec 04 section 17). Scenarios are not evaluated here. | Compare against the last occupied day (`end - 1`): one line. |
| D3 | The record | a new type; `Diagnostic` | `Diagnostic("W_DEADLINE", message, "/objects/<id>/deadline", details=...)`, `details` `{object, endpoint, finish, deadline, daysLate}` (calendar days, at least 1). Message: `<id> finishes <finish>, <n> day(s) after its deadline <deadline>`. | n/a (keys are additive). |
| D4 | `chrona schedule` | stderr lines (as `render`); a stdout field | A stdout `warnings` array, always present, after `diagnostics`; each item is the one diagnostic record (`code`, `severity: warning`, `component: core`, `sourceRef`, `revisionRefs`, `message`, `details`), built by `failure_report.diagnostic_record` (it gains a `severity` keyword). Exit code stays 0. `diagnostics` stays `[]` on success. The three schedule goldens gain `"warnings": []`. | Omit the key when empty (goldens revert). |
| D5 | MCP `schedule_project` | none; a field | A `warnings` field, always present, in the `render_draft` warning shape (`code`, `severity`, `component`, `sourceRef`, `message`, `detail` = the details, keys sorted). Spec 66 and the output schema say so. | Drop the field and the schema entry. |
| D6 | `render` | none; stderr | `W_DEADLINE` joins `warning_ledger` (stderr JSON, Scene diagnostics list, MCP `render_draft` `warnings`). The SVG is byte-identical with and without a violation. | Remove the ledger family. |
| D7 | `chrona validate` | evaluate fixed dates only; evaluate everything; leave it | Leave it, and say so. A deadline is judged against placements, `validate` computes none and is documented as structural ("a cyclic plan validates"); a partial check on fixed objects would be wrong exactly where a derived gate matters. `chrona schedule` is the check. Spec 66 and the MCP description already send an agent to `schedule_project` before calling a plan valid. | Make `validate` schedule (a contract change owned by #780). |
| D8 | A deadline that is not a date | ignore; reject | `validate_project` rejects `2027-02-30` as `E_SCHEMA` at `/objects/<id>/deadline` (as `constraints.at.min` and `fixed-span` dates already are), because the value is now read. | Skip an unparseable value silently. |
| D9 | Terse | a clause; none | No spelling in this slice. A clause (`deadline D`) is a new keyword with its own grammar, source map, N-rules and fixtures in Spec 65, which #148 owns; it is not a trivial map. The ledger line stays `yaml-only` and its reason is reworded (it is not a date, it is checked by `W_DEADLINE`). A terse plan has no deadline, so it never warns. Successor issue recorded on #792. | Add the clause in a terse slice. |
| D10 | View mark | now; successor | Successor issue (design 6.3, item 3): a deadline mark or role is a View, Layout and Scene design. | n/a |

## 4. Design

**Function.** `deadline_warnings(project, placements) -> tuple[Diagnostic, ...]` in Project object order; skips an object with no
`deadline` or no placement; `finish = placement["at"]` when present, else `placement["end"]`; `late = finish - as_date(deadline)`;
emits when `late.days > 0`. Pure; no calendar; no I/O. Core imports nothing outside Core.

**Callers.** `usecases/project_checks.py::schedule_project_mapping` computes warnings after a successful schedule and stores them on
`ProjectSchedule.warnings` (a rejected schedule has none). `usecases/render_review.py::_project_review` computes them beside
`attachment_warnings` and `warning_ledger.collect_render_warnings` gains the family. `app/cli.py` prints them (D4);
`app/agent_tools.py` returns them (D5). The scheduler, `validate`, View, Layout, Scene and the renderers do not read `deadline`.

**Failure behavior.** A deadline never rejects, never alters a placement, a verdict, the analysis, or exit code 0. A rejected schedule
returns no warnings (there are no placements to judge).

**Architecture review.** Layering: Core function, use-case assembly, adapters serialize; import direction unchanged. Q-SCHED-2 and
Spec 04 section 19 ("deadlines do not constrain scheduling") are tested, not assumed. The pair "derived gate plus deadline" is
complete in meaning: `scheduled-point` computes, `constraints.at.max` rejects, `deadline` warns. Risk: the new `warnings` key of the
CLI is a public JSON change; it is additive and its three golden changes are reviewed (D4).

## 5. Implementation plan

| Unit | Content | Gate |
| --- | --- | --- |
| A (this PR) | This record | conformance (docs-only) |
| B (`I792-S1`) | Code, Spec 04 sections 10 and 23 and 20.4 sentence, Spec 66, `core-v0.1-diagnostics.md`, the skill and `mermaid-or-chrona.md` statements that become false, the terse ledger wording, tests | focused tests, conformance, byte identity, mutation check |
| C (`I788-S4`, if small) | `docs/guides/cli-reference.md` (generated; `details`, `warnings`), tutorial only if stale | documented-commands check |
| D | Acceptance reviews for #792 and #788 | `check_issue_acceptance_reviews.py`, exact-main three-OS run |

**Tests (B).** Unit: point, span, rollup, equal, later, none, unplaced; ordering; a fixed-span task and a derived gate (the issue's
case). Inertness: a violated deadline changes no placement, verdict or analysis. CLI: `schedule` prints the warning with `details` and
exit 0; goldens. MCP: `schedule_project` carries `warnings`, the output schema validates it. `render`: stderr line, SVG byte identical
with and without. Corpus sweep: no committed Project warns (every value on or after its date). `validate`: unchanged output with a
violated deadline (D7), and `E_SCHEMA` for a non-date (D8). Each new assertion is mutation-checked (flip `>` to `>=`, drop `end`
fallback, drop a caller) and the result recorded in the PR.

**Must not.** Read `deadline` in the scheduler; add a View mark or vocabulary entry; touch #810 (`_analyze_criticality` backward pass),
#789 (determinism), #780/#781, #782, or #454.

## 6. Progress

- Unit A merged as #818. Unit B (`I792-S1`) implemented as specified: `core/deadlines.py`, `ProjectSchedule.warnings`, the `schedule`
  and MCP `warnings`, the render ledger family, `E_SCHEMA` for a non-date deadline, Spec 04 section 10, Spec 66, the diagnostics
  table, the skill, `mermaid-or-chrona.md`, the guide row and the terse ledger reason. Implementation notes: `_project_review` now
  returns a fourth element (the deadline warnings; two white-box tests unpack it); the CLI characterization goldens changed in
  exactly three lines (`"warnings": []` in the three successful `schedule` cases) and gained four cases (a violated deadline in
  `schedule`, `validate` and `render`, and a non-date deadline); the committed corpus sweep (`corpus`) finds no warning.
- Unit C: nothing to do. `docs/guides/cli-reference.md` is generated from argparse flags and has no prose; the tutorial has no stale
  statement. Unit D follows.

