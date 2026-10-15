# Issue #1545: technical-print details (row-number suffix, per-column text role, header rule)

Baseline: `origin/main` d2992523a. Authority: the reviewer decisions of 2026-10-15 on #1545 (binding). Board #454 row 1.
Gap record: `docs/diagnostics/technical-print-vocabulary-gaps.md` rows 3 and 5. Reference: image on #425
(`docs/research/presentation`).

## Acceptance rows and basis

| # | Row (literal, from the issue) | Basis | Plan |
| --- | --- | --- | --- |
| 1 | Optional literal `suffix` on the `rowIndex` column source, e.g. `{source: rowIndex, suffix: "."}`; Layout measures the full text; no format language | Issue decision 1 | `suffix` is an optional string property of a lane-table column and of a `tableColumns` column. The cell text is the row number followed by the literal; it is measured and set as ordinary cell text, so Layout measures the full text. Valid only when `source` is `rowIndex`; any other source is `E_VIEW_COLUMN_SUFFIX` (flat table) / `E_VIEW_LANE_TABLE_COLUMNS` (lane table). Absent: cell text and output unchanged. |
| 2 | Optional per-column `textRole` on lane-table and table columns naming a Theme text role; unknown roles rejected as today; technical-print declares a monospaced role for the Owner column | Issue decision 2 | Already in the schema and parsed for both column kinds (#1062 flat, #1517 lane) and honoured when cells are built. Gap found: the unknown-role check (`validate_table_text_roles`) reads only the flat `tableColumns`, so a lane-table `textRole` the Theme lacks is not rejected. Fix: the same check covers `rows.laneTable.columns` (`E_THEME_ROLE_REQUIRED` at `/body/rows/laneTable/columns/N/textRole`). technical-print declares `tableCellMono` (`mono` family) and the Owner column names it. |
| 3 | Optional Theme stroke for the column header rule (`tableColumnRule`), drawn under the header across the table's own width only, not the timeline | Issue decision 3 | A Theme text-neutral stroke role `tableColumnRule` (properties `stroke`, `strokeWidth`, `opacity`; colour from `tableColumnRule.stroke`). When the Theme declares it and the surface has a table with a header, table layout (`compose_table`) emits one horizontal Path at the header block's bottom edge from the table's inline start to its inline end. Scene emits it as a `decoration` Path (`tableColumnRule`). No View property, no heading or annotation change, no surface-decoration (row band/rule) change. Absent role: nothing emitted, output unchanged. |
| 4 | Adopt all three in the bundled technical-print View/Theme, view as PNG | Issue | View: `{source: rowIndex, suffix: "."}`, Owner `textRole: tableCellMono`. Theme: role `tableCellMono`, role `tableColumnRule` with `tableColumnRule.stroke: text`. PNG rendered on `examples/halcyon-1` and read. |
| 5 | Update the gaps record | Issue | Rows 3 and 5 and the Follow-ups. |

## Monospaced face

Packaged: `Noto Sans Mono` regular (400), `src/chrona/resources/fonts/noto-sans-mono-regular-v1.ttf`, in `chrona.noto-sans`
(`default-font-metrics.yaml`, `font-sets.yaml`). The technical-print Theme already binds `mono: Noto Sans Mono, monospace`
for the axis and legend. `tableCellMono` reuses `mono`, so no new family is introduced. Machine without the face: not
possible for the packaged default Render Context (the face ships in the wheel). A Render Context that names a font set
without Noto Sans Mono falls through per #1495: `W_FONT_FAMILY_SKIPPED` for the unavailable family, then the next family
of the list, then installed fonts; `E_FONT_GLYPH_UNAVAILABLE` only for a glyph no candidate has (initials are Latin
letters, so in practice none). Nothing in this change alters that path.

## Ownership and risk

Layout owns the rule geometry (table header region); Scene carries a completed Path; adapters serialise it (no typeset
files touched). Not touched: annotation containers, heading layout, mark geometry, terminals, surface decoration, Marquee.
Schema changes are additive (`suffix`; no new required property); `python -m tools.schema_equivalence --base-rev origin/main`
is run. Side effects on public output: none expected (no public slide uses technical-print); verified with
`tools/regenerate_public_examples.py --check`.

## Tests

Synthetic unit/integration tests: suffix measured in the cell text (lane and flat), suffix rejected on other sources,
lane `textRole` unknown-role rejection and the role reaching the cell, header rule present only when the role is declared,
spanning the table width and not the timeline, and absent-knob byte identity. Packaged technical-print columns test updated.
