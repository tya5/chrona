# Issue #429, slice I429-3: the Muted executive preset (work record)

Living record. Public base: `4aab0b9b9` on `main`. Reference: the Muted executive prompt on #425 (copied in #429's body). Refs #429.

## Baseline

- The catalogue lists editorial, technical-print, marquee, sunday, target-b (library.yaml); `muted-executive` was absent (acceptance review of 2026-10-15, row 1).
- #479 (`grouping.order: {by: earliestPlannedStart}`), #486, #426, #490 are closed; the vocabulary below exists on main.
- Literal acceptance this slice serves (#429): four presets ship, reproduce byte-identically (row 1); a preset is selectable by name (row 3); the reference differences are recorded as named gaps (row 4).

## Design: vocabulary per treatment

| Reference treatment | Layer | Vocabulary used |
| --- | --- | --- |
| Group header rows, in a data-derived order | View | `grouping: {by: objectType, order: {by: earliestPlannedStart}, presentation: header}`; no group value or order is named |
| Group bands slightly darker | Theme | roles `group-band`, `group-header-band` (fill `surfaceRaised`); `backgroundDecoration: {rows: rules, groups: all}` with role `row-rule` |
| Numbered rows, Task, Owner names | View | `tableColumns` with `source: rowIndex`, `title`, `{field: owner}` (a field key, no value) |
| Solid bar, 2px radius | Theme | `planned` with `markHeight/markOffset` tokens and `mark-radius-capsule: 0.12`, fill `category:bar` |
| Dashed baseline outline above the bar | View + Theme | View `comparison.baselineMarks: ghost-when-changed`; Theme `snapshot` role with `pattern: outline`, `dash: dash.baseline`, height 0.28 at offset 0.06 against the bar at 0.42 |
| 45-degree squares | Theme | `milestone-symbol` shape `diamond` |
| Dashed amber today marker | Theme/Scheme | `dash.as-of`, `as-of.stroke: accent` (amber) |
| Two-tier date band, sentence case | View + Theme | `axis.tiers` quarter and month bands with `axisQuarter` / `axisMonth` lane heights (44 and 38), label forms `quarter`, `short-month`, `textTransform: none` |
| Palette: warm greys, one blue, one amber | Scheme | `surface`, `surfaceRaised`, `text`, `category:bar` (blue), `accent` (amber) |
| Legend strip | Detail Profile + Layout | Planned, Baseline, Milestone, Dependency, Today, Non-working day; Layout inherited from the Editorial bundle (horizontal legend) |

The actual mark (drawn whenever Actual data exists) is a thin light strip inside the bar; the reference has none, it only has to be a valid, contrast-passing role.

## Named gaps

Recorded in [muted-executive-vocabulary-gaps.md](../../diagnostics/muted-executive-vocabulary-gaps.md): dashed baseline not reachable by `render --preset` (no Snapshot on a draft); critical dependencies not distinguishable on the table-timeline; one weight short of three; generic `objectType` group names; group band table-only; number column width; no variance legend swatch. No capability was invented and no design YAML or `examples/**` was edited.

## Slice plan and evidence

Files: `presets/bundles/muted-executive/{view,theme,scheme,layout,detail}.yaml`, a `library.yaml` entry (appended, so existing listing order is unchanged), `docs/guides/first-project.md`, the CLI characterization golden (listing and unknown-id message), `tests/integration/test_muted_executive_preset.py`. No schema is touched. Existing parametrized tests (generic-values scan, Halcyon preset rules, typeset targets, copy, without-examples) pick the preset up from the library.
Evidence: the baseline was checked in a scratch Render Context (not committed) over a copy of halcyon-1 with a Snapshot: 7 dashed baseline outlines were drawn, each above and narrower than its bar (for example block 1443.3 to 1452.9 against the bar 1455.6 to 1472.6).
A gallery slide (`examples/**`) is reviewer work and is not part of this slice.
