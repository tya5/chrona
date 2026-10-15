# #1529: adopt lane table columns in the `technical-print` preset

Status: design record, 2026-10-15. Base: `origin/main` 9402ef0a7. Refs #1529 (successor of #1517 row 2, PR #1525).
Related: [#1517 note](issue-1517-lane-table-columns-2026-10-15.md),
[technical-print gaps](../../diagnostics/technical-print-vocabulary-gaps.md) rows `lane-table-columns`, `table-header-role-undeclared`.

## Acceptance (issue text, literal)

Declare `columns [rowIndex, label, {field: owner, transform: initials}]` in the bundled `technical-print` View
(golden and tests re-recorded, side-effect counts in the PR); mark gap `lane-table-columns` resolved. The `1.`
punctuation is out of scope. The gaps record also says the header role `tableColumnLabel` is delivered (#1015) but not
declared by the bundled Theme (`table-header-role-undeclared`), so the Theme declares it bold.

## Change

| File | Change |
| --- | --- |
| `bundles/technical-print/view.yaml` | `rows.laneTable.columns`: `rowIndex` (id `'No'`, quoted: a bare `No` is a YAML boolean), `label` (id `Task`), `{field: owner}` + `transform: initials` (id `Owner`); `count: auto` and `text` kept |
| `bundles/technical-print/theme.yaml` | `typography.tableColumnLabel` role: the `text` role with `weight.bold` |
| gaps record | rows 3 and 5 updated; the header rule under the table stays unmeasured |

Lane `packing` is unchanged (`rows.mode: lanes`). Public examples: none of `examples/**` uses `technical-print`
(checked by search and by `regenerate_public_examples.py --check`), so no example delta is expected.
