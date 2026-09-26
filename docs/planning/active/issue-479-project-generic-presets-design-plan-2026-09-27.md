# Design Plan — What Project-Generic Presets Cannot Express (#479)

**Public base:** `89f2718b` on `main`. **Source of truth:** [Issue #479](https://github.com/tya5/chrona/issues/479); Specifications 06, 38, 45, 60 and 62 (declarative presentation packages); #421 (scale separability, landed); #427 (legend miniatures, landed); #467 (lanes, in progress, migrates preset Views).

## Published baseline

- **`grouping.order`** accepts only an explicit value list (`projection.py` sorts by list index, then key), so a generic preset gets alphabetical groups.
- **A project with no grouping field** puts every row into the `missing` group (`Other` in the presets), which renders as a single header over every row.
- **`colorEncoding`** needs a `domain` list in the View and a `colorScales.<id>.slots` value map in the Theme. The bundle Themes carry HALCYON's `owner` values (`bus`, `payload`, `ait`, …), which are project-specific.
- **A preset package** has four members (`presentation-preset-v0.1`). Legend entries live in a Review Detail Profile that a preset cannot carry, so a preset's `legend` slot renders empty unless `--detail` is passed.
- **Visual profile:** the CLI default `--visual-profile` is `v0.5-baseline`, and a preset cannot state that it needs `v0.7` (#478 now reports the omission, but cannot choose).
- **`labels.placement`** is `plot | table | none`. The presets rely on the table title column staying while labels are in the plot, but that combination is not a declared choice.

## Literal acceptance ledger

1. “`grouping.order` accepts a data-derived order, at least by earliest planned start.”
2. “When every item falls in the missing group, header grouping renders no header, or the View can declare that.”
3. “A colour encoding can assign a categorical palette by order of first appearance, without a value list.”
4. “A preset can carry legend entries, either as a fifth member or in the View.”
5. “A preset can declare a required or preferred visual profile.”
6. “Names in both the table and the plot is a declared placement.”
7. “The five catalogue presets use each of these where relevant, and render HALCYON-1 and the starter without project-specific values.”

## Sequencing

This takes the View version after #467's (expected v0.27). Its preset-View edits must land after #467 L3, which migrates the preset Views to lanes. Design now; implement once the queue has landed.
