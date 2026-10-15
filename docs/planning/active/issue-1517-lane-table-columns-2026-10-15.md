# #1517: lane table columns (`rowIndex`, `field`, `transform: initials`)

Status: design and implementation record, 2026-10-15. Base: `origin/main` 2e1b6313d. Refs #1517.
Related: [#1373 row 2 note](issue-1373-initials-cell-2026-10-15.md) (the `initials` transform),
[technical-print gaps](../../diagnostics/technical-print-vocabulary-gaps.md) gap `lane-table-columns`.

## Baseline and acceptance

Issue text (literal): a lane View's `laneTable` has only a label (and count), so the `technical-print` View renders one
`Lane` column; `tableColumns` (`rowIndex`, `{field: owner}`, `transform`) belongs to automatic rows, which cannot use
`packing` / `laneKeys`. "Needs: either column sources (`rowIndex`, `field`, transform) on `laneTable`, or automatic rows
with the attached-point and packing behaviour the lane View gets." Reference: header `Task` / `Owner`, rows numbered
`1. Project Kickoff`, owner as monospaced initials.

| # | Acceptance row | Basis |
| --- | --- | --- |
| 1 | A lane View can declare `rows.laneTable.columns` with a `rowIndex` column | issue "column sources (`rowIndex`...)" |
| 2 | ... with a `{field: <name>}` column | issue "(`field`...)" |
| 3 | ... and `transform: initials` on a field column | issue "transform"; #1373 note |
| 4 | Lane `packing` is unchanged (the View stays `rows.mode: lanes`) | issue "automatic rows with ... packing" is the other option; the first option is taken |
| 5 | Absent `columns`: byte-identical output | task: additive and optional |
| 6 | Misdeclarations are refused with a named code | closed-set discipline (Spec 46) |

Not in the issue and left out: the `1.` punctuation after the number, a header role (`tableColumnLabel` is a Theme
matter), and the bundled `technical-print` View (adoption is a follow-up PR; this PR does not change it).

## Grammar

`rows.laneTable.columns`: optional array (minItems 1) in `view-v0.28`, declared in place (Spec 56 section 3.2, additive
optional member). Each entry: `id` (the header text, as for `tableColumns`), `source`, optional `transform`
(`initials`), `missing` (default `em-dash`), `align` (default `start`), `textRole`.
`source` is one of `label` (the lane label cell that exists today), `rowIndex`, or `{field: name}`.
Exactly one `label` column is required: it keeps the lane label and is where the column order is chosen, so
`[rowIndex, label, {field: owner}]` reads number, task, owner. Absent `columns`, the table is the label column headed
`Lane` as before. `count` stays a separate trailing `Items` column and composes with `columns`.

## Semantics (deterministic)

| Source | Value for a lane row | Basis |
| --- | --- | --- |
| `label` | the existing lane label | unchanged rule (Spec 38) |
| `rowIndex` | 1-based position of the lane row in table order | `tableColumns` `rowIndex` meaning |
| `{field}` | the field of the lane's first member (`memberItemIds[0]`) | the same member the `label: lane` singleton label already reads; a multi-member lane is summarised by its founder |

A field absent on that member reads as absent: `missing` text. `transform: initials` reuses #1373 `display_value`
unchanged (an all-punctuation value reads as `missing`; a non-text value is `E_VIEW_COLUMN_TRANSFORM` at run time).
Cells are completed text before measurement, as in `tableColumns`; Layout and Scene gain no new concept.

## Diagnostics

`E_VIEW_SCHEMA` for shape; ingress `ContractError`: `E_VIEW_LANE_TABLE_COLUMNS` (no or more than one `label` column,
duplicate ids, an id equal to the reserved `Items` when `count` can show, a `transform` on a non-`field` source),
`E_VIEW_COLUMN_TRANSFORM` is not reused for the last because the source set differs.
The generated inventory is bot-owned and not edited.

## Layers and files

View declares (`schemas/view-v0.28.schema.yaml`, `contracts/resources.py` `ViewLaneTable.columns`); the lane table
normalizer (`review/v05_content.py` `_lane_table_content`) builds the cells; Layout reads column ids from the
`TableContent` it receives, with the label column keeping the internal id `Lane` that sizing already uses. Spec 38 and
Spec 46 get a paragraph; one L1 line in `conformance/schema-equivalence/expected-deltas-v0.1.yaml`.
Tests: `tests/integration/test_lane_table_columns.py` (ASCII / `\u` only); the schema identifier-site count for `view-v0.28` `non-empty-string` rises 16 to 17 (the header-text `id`, as `tableColumns[].id`). `tableColumns` stay invalid in lane mode, so
the lane resource migration inventory ("non-design presets are lane Views with no tableColumns") is unaffected.

## Successors (recorded, not done)

1. Adopt in the bundled `technical-print` View with `tableColumnLabel` in its Theme (separate PR).
2. A literal affix (`1.`) for `rowIndex`; `affixes` today carry only signed-value and `missing` states.
