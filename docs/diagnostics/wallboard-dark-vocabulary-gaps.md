# Wallboard dark: the reference elements chrona does not express (#429 row 4)

The `wallboard-dark` catalogue preset was built from the generated reference in #425 (Wallboard dark prompt). This report
names every element of that reference the preset does not reach, with the capability it would need. Work record:
[issue-429-wallboard-dark-2026-10-15.md](../planning/active/issue-429-wallboard-dark-2026-10-15.md).

| # | Reference element | Status on main | Needs |
| --- | --- | --- | --- |
| 1 | A fill per calendar quarter: blue Q1, green Q2, brown Q3, purple Q4 | not reachable by a generic preset: an `interval` key is the window-relative ordinal of every retained interval, and the Theme `slots` mapping must name the whole domain exactly with no recycling (Spec 60 section 7). A preset would have to fix the window length. The preset uses the `alternating` key, which holds for any window: two quarter hues (blue, green) in turn | a key that is the calendar quarter of the interval (a closed domain of four), or a mapping that cycles a declared palette over an open ordinal domain |
| 2 | Each month on a darker tint of its own quarter | reached: the month tier keys `alternating` through `containingTier: 0`, so a month takes the tint declared for its quarter's parity | none |
| 3 | A two-tier band whose tiers carry their own fills and short labels | reached (#1518): the packaged View retains both `fillScale` bands and declares quarter/month labels (`Q1` / `Jan`) with matching `axisQuarter` / `axisMonth` typography; rendered SVG regression proves separate aligned lanes | none; heights, paint and borders remain Theme tuning |
| 4 | A category mark in the Owner cell (a coloured dot per owning team) | not expressible generically: a `visualEncodings` cell target names its object, column and every domain value with its icon, so it names project values. The bar colour per owner is reached (`colorEncoding` over the owner field, six palette slots, cycled) | a cell encoding whose domain is the field's first-appearance order and whose mark is the scale colour, with no value named |
| 5 | Heavy weights and a geometric sans | not expressible with the packaged fonts: only Noto Sans 400 and 700 have metrics and font files; the table body stays 400 and the axis, heading and group text are 700 | a packaged heavier face, and a geometric family |
| 6 | Today marker with a filled label chip and a bare word | reached (#1563): bare `Today` uses the existing absent-date marker policy; the Theme's `as-of-label-chip` draws the accent ground behind dark ink, measured by Layout | none; existing marker date and Theme chip controls suffice |
| 7 | Seven filled circles in the legend, drawn horizontally | five authored keys now use filled circles in the inline legend; generated palette keys retain their default squares; PNG viewed | per-entry circle delivered (#1562); generated-key default remains a design decision |
| 8 | Heavy 32px bars with fully rounded ends | reached by tokens: the bar is `mark-height-bar` 0.56 of the row from offset 0.22 with `mark-radius-capsule` 0.5 | none |
| 9 | Large filled chevron milestones | `planned.symbolHeight` makes points larger than bars; shape-aware Layout completion retains the declared chevron rather than substituting a rounded diamond; corrected PNG viewed | existing size token reused; shape correction and native-shape/radius tests delivered (#1562) |
| 10 | Six saturated team colours | six Scheme categories, assigned in first-appearance order and recycled after six owners (`palette`); a seventh owner repeats the first colour | none identified (cycling is the declared palette rule) |
| 11 | Table rows numbered, group header rows | not part of this reference; the View has no grouping (`by: none`), so `test_first_run_lane_order` holds without a name | none |
| 12 | Rows as a lane table | the preset is an automatic-rows table View (Task and Owner `tableColumns`), so `test_lane_resource_migration_inventory_and_editorial_mirror` excludes it by name, as it does `muted-executive` | a lane table with an owner column |

Colour: the near-black ground, 4% raised row band, bright text and the six series colours are Scheme values; every `contrast` check of the packaged set (mark contrast, state-text contrast, decoration contrast) passes with no warning on a halcyon render.
The preset names no project field value, group order or wording; the only field key it names is `owner`, as `control-room-dark` does.
