# Technical print: the reference elements chrona does not express (#429 row 4)

The `technical-print` catalogue preset (`src/chrona/resources/presets/bundles/technical-print`, gallery slide 14, I429-2) was
built from the generated reference in #425 (Technical print prompt and image). This report names every difference between
the preset's rendered slide and that reference. The reference image was read directly (1672 x 941); the render is
`chrona render --preset technical-print` over `examples/onboarding/07-actuals` (project and actual set) and over
`examples/aster-ssd`, at `f09e4ff44`. Measurements are by eye from those images unless a number is cited from #425.

| # | Name | Reference shows | Chrona draws | Missing capability | Tracked in |
| --- | --- | --- | --- | --- | --- |
| 1 | `overrun-actual-colour` | the inner bar of one task (UAT) in red; all others black | one black actual role for every task | a Theme binding for the actual mark per variance class. Established from the role registry and theme, not rendered with an overrun fixture | #1516 |
| 2 | `legend-variance-swatch` | a red rect swatch, "Overrun (behind schedule)" | no entry; adding `variance-behind` to the legend is rejected with `E_PRESENTATION_PRIMITIVE_INVALID` (reproduced) | a legend swatch for variance roles with no text contrast treatment | #1515 |
| 3 | `lane-table-columns` | header `Task` / `Owner`; rows numbered `1.` to `8.`; owner as monospaced initials | one column headed `Lane`, no numbers, no owner | `rowIndex`, `field` and `transform: initials` sources on a lane table (they exist on `tableColumns` of automatic rows only) | #1517 |
| 4 | `axis-two-tier-short-labels` | a Q1 to Q4 row over a Jan to Dec row, white cells with hairline borders | one black band reading `Sep 2026`, `Oct 2026`, over an unlabelled halftone band | a quarter band over a month band with `Q1` / `Jan` label forms | #1518 |
| 5 | `table-header-role-undeclared` | header in bold with a rule beneath (the rule spans the table only) | header `Lane` in the regular body role; no table-side rule | none for the role: `tableColumnLabel` exists since #1015 and the bundled Theme does not declare it. The header rule under the table is not measured as expressible | bundle follow-up (below) |
| 6 | `open-circle-milestone` | open circle, hairline, about 20 px on a 36 px bar row | the pin glyph (`chrona-starter:pin`) | reachable without new capability: in a scratch copy, `milestone-symbol: {shape: circle}` with `milestone.fill: surface` and `milestone.stroke: text` draws an outlined circle-like mark. It takes the full mark size (about 38 px, squarer than a circle). `milestoneSymbol` accepts no `pattern` or `strokeWidth` (`E_THEME_ROLE_PROPERTY_UNSUPPORTED`). The handoff's "no outline-only glyph treatment" holds for catalogue glyphs, not for the `circle` shape | bundle follow-up (below); a smaller milestone size is not measured as expressible |
| 7 | `open-arrowhead-unused` | small open (outline) arrowheads | filled triangle (`arrow` marker, `shape: triangle`) | none: `shape: open-triangle` exists (#1042); the bundle does not use it | bundle follow-up |
| 8 | `today-ink` | black dotted line, label `Today` | dotted line in the Scheme `accent` (red), label `Today` without a date (#428 resolved) | none: `as-of.stroke` binds `accent`; the reference keeps red for variance only | bundle follow-up |
| 9 | `row-band-and-bar-labels` | white ground; no bar labels | grey `surfaceRaised` band behind every table row; each bar labelled `title` and finish delta (`Design +0d`) | none: `groupBand: table` and the View `visibility.labels` content are preset choices | bundle follow-up |
| 10 | `non-working-day-rules` | two thin vertical rules per closed span | a pair of outlined rects (reached); legend swatch is a grey square, not the double rule | a legend swatch shape for a pair of rules (#427 delivered horizontal swatches, not this shape); not measured further | none |
| 11 | `open-actual-glyph` | every task shows a black bar inside the outline | a task whose actual is open (`openUntil: asOf`, progress 0.4) shows a pin-shaped glyph inside the outline, not a bar | not investigated; observed on `07-actuals` Build only | not measured |
| 12 | `monospaced-legend-and-axis-type` | legend in the grotesque; axis in monospace | legend and axis in Noto Sans Mono | none: the `legend` role binds `mono` | bundle follow-up |

Reached as drawn: outline planned with an inset black actual at 0.389 of the container (36 px bar, 14 px inner, #425),
square ends, hairline weight, orthogonal dependencies, the as-of marker label without a date, the horizontal legend, and
non-working days as outlines rather than a tint.

## Fix claims checked

- **#1015 (header role): delivered, not used by this preset.** `tableColumnLabel` is read when a Theme declares it
  (`ThemeTokenView.table_header_role`); `technical-print/theme.yaml` has no such role, so the header is regular weight.
- **#1373 row 2 (`transform: initials`, PR #1509): delivered, not reachable from this View.** The View schema accepts
  `transform: initials` on a `field` column of `tableColumns`; `technical-print/view.yaml` is a lane View
  (`laneTable: {label: lane}`) that has no `tableColumns`.

## Follow-ups (not in this PR; the bundle is not changed here)

1. Declare `tableColumnLabel` (bold) in the Theme and switch to `tableColumns` with `source: rowIndex`, `title` and
   `{field: owner}` with `transform: initials`, as the Editorial and Muted executive bundles already name `{field: owner}`.
   Switching to automatic rows gives up lane `packing`, which is gap 3 (#1517); decide whether that trade is wanted.
2. Use `milestone-symbol: {shape: circle}` with the outline bindings from row 6, `open-triangle` for `arrow`,
   a black `as-of.stroke`, no row band, and no finish-delta bar label, one change at a time with a render.
3. Declare the axis cells in the reference's own terms (white `axis-band-decoration` fill, hairline separators) once #1518
   admits two labelled tiers.

Palette: black, white and one red (`accent`, `negative`) are carried by the Scheme; no further hue is used beyond the
`positive` and `warning` entries the Scheme keeps for variance and exception roles.
