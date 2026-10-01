<!-- chrona:literal-acceptance/v1 -->

# Issue #780 — `validate` and dependency cycles acceptance review

Source: [Issue #780](https://github.com/tya5/chrona/issues/780), observed 2026-10-02 (body plus one comment, mine, the claim and decision record; last updated 2026-10-02). The issue's acceptance section has one checkbox; the table copies it literally. Design and plan: [work record](../../planning/active/issue-780-validate-dependency-cycle-work-record-2026-10-02.md).

Slices: docs [PR #819](https://github.com/tya5/chrona/pull/819) (`1e5caa92`); implementation [PR #828](https://github.com/tya5/chrona/pull/828) (`625dc04f`).

## Literal issue acceptance

### Issue #780

- Source: [Issue #780](https://github.com/tya5/chrona/issues/780)
- Observed: 2026-10-02

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | A cycle is reported with a code that names it, by the command the spec says reports it, with a test for a fixed-span cycle and a non-fixed cycle (duration or point modes). | met | Code: the specified `E_UNSUPPORTED_CYCLE` (or `E_UNSATISFIABLE_DEPENDENCIES` for a positive loop) rather than a new code, decided on the issue (Spec 04 section 16 calls a cycle a capability limit, not a Core error); the finding names the objects on the cycle and points at the relation that closes it (`/relations/<index>`). Command: `validate` and `schedule` report it identically because both call [`project_checks`](../../../src/chrona/usecases/project_checks.py) over the pure [`dependency_cycles`](../../../src/chrona/scheduling/dependency_cycles.py); the same holds for the MCP tools (`test_validate_reports_a_cycle_exactly_as_the_cli_and_schedule_do`, stdio `test_status_and_error_flag_over_stdio`); Spec 04 section 16, Spec 66 and the skill state it. Tests ([`test_project_checks_cycles.py`](../../../tests/unit/chrona/usecases/test_project_checks_cycles.py)): fixed-span (the issue's reproduction, the starter's two fixed spans), duration, point, fixed with duration, an acyclic-by-endpoint wait cycle, self relation, rollup on its child, both codes against the scheduler, plus not-a-cycle cases (nested start-to-start and finish-to-finish in a fixed span, a negative-lag fixed loop, a chain). The reproduction failed on `main` before the change (failing-first commit in the PR); eight mutants of the implementation were each killed by a named test (PR description). | — |

## Programme-level criteria (optional)

None.

## Architecture and release conclusion

The fix sits in a shared use case, so no adapter has its own cycle logic; `core.validation` and `scheduling/scheduler.py` are untouched (the scheduler's positive-loop proof is reused by import), and `W_DEADLINE` (#810), `totalFloat` order (#789) are not affected. The CLI characterization golden changed for exactly two records, `validate-cycle-rejected` (renamed from `validate-cycle-passes-validation`, exit 0 `[]` to exit 1 with one finding) and `schedule-cycle-rejected` (two unnamed per-object findings to one named finding); the diff was reviewed in the PR.

Disclosures:

- `render` still reports the scheduler's own diagnostic for a cycle (same code, old wording, at the first waiting object); naming the cycle there needs a scheduler edit and was left out on purpose. A terse plan therefore positions a `schedule` cycle at line 3 and a `render` cycle at line 2 (`tests/cli/test_plan_dispatch.py`).
- Intended behaviour change recorded on the issue: two fixed gates on one date that depend on each other with `0d` scheduled before and are now a cycle.
- The check runs only after Core validation accepts the Project, so a structurally broken plan reports its own error first.

Exact review-bearing-main three-OS CI and newest-Python materializer run must pass before closing #780; record that run in the issue closing comment.
