<!-- chrona:literal-acceptance/v1 -->

# Literal acceptance review: #1856 rows 1 to 2

Observed on `main` at `b1935990b` (the derived-sync bot commit after [PR #1923](https://github.com/tya5/chrona/pull/1923); the later tip only adds a docs PR). [Issue #1856](https://github.com/tya5/chrona/issues/1856) has no numbered rows; its `Acceptance:` block holds two bullets. The body and its comments were re-fetched with `gh issue view 1856 -R tya5/chrona --json body,comments` on 2026-10-22: the issue has no comments, so the count is two rows. The issue is the follow-up of row 4 of the [#1827 review](issue-1827-acceptance-review-2026-10-21.md) (its four named legend entries became sentence case in #1833; the four lower-case fragments this issue names remained). Landed in [PR #1868](https://github.com/tya5/chrona/pull/1868) (`60b9a17ca`, the reviewer chose option 1 of the first bullet: state the exception, change no value). No row is narrowed or open.

## Method

Private venv `/private/tmp/claude-501/venv1682`, `PYTHONPATH=<worktree>/src:<worktree>`, worktree on `b1935990b`, no shared install. The focused file is [pytest-1856.txt](assets-1856/pytest-1856.txt) (25 passed, the full suite was not run). The guard was also run against two in-memory mutations of the catalog, [guard-probe-1856.txt](assets-1856/guard-probe-1856.txt) (script: [probe-1856.py.txt](assets-1856/probe-1856.py.txt)); nothing on disk was changed.

## Literal issue acceptance

### Issue #1856

- Source: [Issue #1856](https://github.com/tya5/chrona/issues/1856)
- Observed: 2026-10-22

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | either the guide and Spec 63 name the fragment exception (keys that are drawn inside another text, and units), or the values are changed and every public slide that draws them is counted; | met | First alternative, no value changed. The guide's "Case belongs to the design" says "Exactly six `en-US` values are not sentence case": four keys drawn inside another text (`marker.baselineNew`, `marker.baselineRemoved`, `missing.unknown`, `missing.inProgress`) and two unit symbols (`delta.unit.calendarDay`, `delta.unit.workingDay`) ([`locale-and-wording.md`](../../guides/locale-and-wording.md)); [Spec 63](../../specification/63-axis-name-tables.md) names the same six as "explicit and closed". The table on main has exactly six lower-case `en-US` values of 58, the same keys ([log](assets-1856/guard-probe-1856.txt)). The second alternative is not taken, so there are no slides to count; PR #1868 reports 0 public slides changed. | — |
| 2 | a test that fails when a new lower-case entry appears outside the stated exception. | met | `test_a_lower_case_en_us_value_is_only_a_named_fragment_or_unit_symbol` compares the set of lower-case `en-US` values with the named keys and asserts the unit symbols equal `d` ([`test_wording_tables.py`](../../../tests/unit/chrona/presentation/model/test_wording_tables.py), lines 321 to 335; passes, [log](assets-1856/pytest-1856.txt)). Run here against the real catalog with one extra lower-case value (`marker.probeNew` = `probe`) it fails with the message that points to the guide and Spec 63, and it also fails when a listed key (`missing.unknown`) becomes sentence case, so the list cannot go stale either ([log](assets-1856/guard-probe-1856.txt)). | — |

Counts: 2 rows, 2 `met`, 0 `narrowed`, 0 `not met`.

## Programme-level criteria (optional)

### Public side effects

This review adds a document, two logs and a script copy under [assets-1856](assets-1856/pytest-1856.txt); it changes no code, schema, specification, guide, preset, design or example.

| Item | Slides changed | New diagnostics | Schema delta |
| --- | ---: | ---: | --- |
| This review | 0 | 0 | none |
