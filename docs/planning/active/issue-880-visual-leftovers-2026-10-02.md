# Issue #880: post-review visual leftovers (work record)

Living record for [#880](https://github.com/tya5/chrona/issues/880): baseline, design plan, design, architecture review, implementation plan and progress. Edited in place; Git keeps history.

**Public base:** `175a7890` on `main`. **Status:** S0 (this record) is merged ([#895](https://github.com/tya5/chrona/pull/895)); see section 6 for the slices. Owner decisions with options, choice, reason and reversal are recorded as a comment on the issue and summarised in section 4.

## 1. Published baseline

#880 has no comments besides this work's claim. It consolidates three notes left on closed issues (#582, #492, #538). Each was reproduced on `175a7890` from committed Scenes (`examples/**/generated/*.scene.json`) and from the rendered images (resvg PNGs of the committed SVG, and a fresh `chrona init` starter rendered with `chrona render ... --emit-scene`).

**Item 1, the named-period band reads as a hole.** `02-programme-board` (Theme `examples/halcyon-1/themes/wallboard.yaml`, scheme `control-room-dark`): `period-band:launch-window` is a 50.7 px wide Rect filled `#0B1220`, the scheme's `surface`, over the plot ground `#142642` (`surfaceRaised`), so it is darker than what surrounds it. The chip (`period-label-chip`) is 117 px wide, wider than the band. None of the eight bundled presets (`src/chrona/resources/presets/bundles/*/theme.yaml`) declares `period-band`, `period-label` or `period-label-chip`, so a View that selects a period under a preset fails with `E_THEME_ROLE_REQUIRED` (decision J5 of #582, which left preset content to the presets lane).

**Item 2, grid overshoot and ghost text.** Two separate causes, both general:

- *Overshoot.* `surface_axis.py` draws a `grid-major` / `grid-minor` line over the whole timeline slot (`timeline.bounds.block_size`), `surface_backgrounds.py` shades each closed day over the whole slot, and `surface_composer.py` draws the as-of line over the whole slot. The rows, group bands and row bands stop at the last row. The slot is taller than the rows whenever the surface is given more room than the rows need (a fixed viewport, a fill lane). A scan of every committed Scene finds 29 surfaces where the three overlays run past the last row: Controller Z `axis-ticks` by 68 px (the reported y 658 to 718 band, 752.8 to 820.8 in Scene coordinates), `halcyon-1/04-tvac-slip` by 794 px, `controller-z/plan-only` by 488 px. It is not that slide's YAML.
- *Ghost text.* The faint text beside bars is the relation labels (`relation-label:*`, for example `end->start`, `end->at +5wd`). Their Scene visual role is `annotation` (`semantic_registry.py`, `relationLabel`), and the Scene paints a Text by its visual role. Every bundled Theme and every example Theme binds `annotation.fill: surfaceRaised` (28 files), a ground colour, so the label ink is `#EAF0F8` on a `#EEF3F8` ground in `controller-z/axis-ticks`. The sibling label `projectNote` has visual role `text` and reads `#172033`. No gate sees this: `relationLabel` has no contrast class.

**Item 3, the axis band stops short.** On a fresh `chrona init` starter (1600xauto), the timeline slot is `[553.3, 1580.0]`. The scale is inset by the point-mark footprint of the last milestone (`mark_aware_scale.py`, #501), so its range is `[570.3, 1562.0]`. Axis band cells, closed-day cells and (if present) period bands are laid out through the scale and end at 1562 (the first cell starts at 571.3). The axis rule (`left, right = timeline slot`) and the row bands run to 1580 and the milestone diamond (1546 to 1580) lies in the strip. Window positions are correct; the margin is simply not painted.

Unverified at baseline: the exact output after each fix (read from regenerated Scenes and images in each slice).

**Related finding, not an acceptance row.** In the same starter every window day is a closed day (78 `calendar-closed` Rects, weekdays included) because a Project with no `calendars` has an empty working-day set (`review/v05_content.py:_calendar_closures`), so the plot is shaded as "weekend". Filed as [#893](https://github.com/tya5/chrona/issues/893); this work does not change it.

## 2. Literal acceptance (copied from the issue)

1. Each item is fixed, or explained as intended, with Scene evidence. Items 2 and 3 get a synthetic check, if they are core rules.
2. Item 1 is fixed through Theme or preset YAML only; no core change.

The issue body also states, per item, the fix. Item 1: give the presets (and the HALCYON slide) a period paint, a light tint or a catalogue pattern, that passes perceptibility as a highlight, and declare the roles in every bundled Theme. Item 2: find whether it is the general grid extent rule or that slide's YAML, and fix it accordingly. Item 3: make band, ground and rule end at the same edge.

## 3. Dependencies and neighbours

- #582 (closed): periods, the roles and `E_THEME_ROLE_REQUIRED` stay as they are; item 1 only adds Theme content. #718 owns packaged presets and parts generally; item 1 is the preset content #582 deferred (J5) and #871 listed.
- #583 (group header, tint) and #587 (surface glow, canvas texture) touch Theme schema and surface files in parallel; #881 is hygiene. This work adds no Theme schema property and keeps shared-file diffs to a few lines each.
- #492 (axis ticks, closed): `tickLength` ticks are unchanged and are not part of the overlay extent.

## 4. Design plan and design

### Use cases

- **U1.** A surface is given more block room than its rows need. Gridlines, closed-day shading and the as-of line end where the plot ground ends, not at the slot edge.
- **U2.** A relation label is drawn in the same ink as every other label, under any Theme, including a Theme that still binds `annotation.fill` to a ground colour.
- **U3.** A scale inset for a point mark leaves a margin inside the plot; the axis band, closed-day shading and named-period bands cover the margin, so band, ground and rule end at the same edge.
- **U4.** A View selects a period under any bundled preset and the band reads as a highlight.

### Decisions (owner level; options, choice, why, reversal are on the issue)

- **J1. Plot extent (item 2a).** The plot's block extent is from the top of the timeline slot to the bottom of the last row (the group content bottom when groups exist), never beyond the slot; with no rows it is the slot. Options: A the overlays follow the ground; B the ground grows to the slot; C leave as is. **Choice A.** The slot is an allocation and the rows are the content; painting the ground to the slot would stretch an empty plot, and C leaves the defect. Layout owns it: one `plot_bounds` fact on the base geometry, read by the axis, the calendar backgrounds, the as-of line and the period band. Spec 50 already says the period band's and the calendar closure's block extent is "the timeline slot's plot rows"; this makes that sentence true. `tickLength` ticks and the axis rule are unchanged. Reversal: `plot_bounds` returns the slot.
- **J2. Relation label ink (item 2b).** Options: A edit 28 Theme files (`annotation.fill: text`), which leaves every user Theme broken; B bind the relation label's visual role to `text`, like `projectNote`; C classify the label as state text and gate it, which would reject every existing Theme that lacks a `contrastTreatment` for it. **Choice B.** One registry line, general, no Theme or schema change; a relation label is a label. Not delivered: a separate Theme knob for relation-label ink (additive later, a `relation-label` role that falls back to `text`). Reversal: restore the binding.
- **J3. Plot edge (item 3).** The plot's inline extent is the timeline slot, so a band cell, a closed-day cell or a period band whose edge is the window edge extends to the slot edge. Options: A extend the three to the slot edge; B shorten the axis rule and the row bands to the scale range; C leave. **Choice A.** The point mark protrudes into the margin (B would cut the diamond's ground), so the margin belongs to the plot. Positions of interval starts, gridlines, labels, the as-of line and marks are unchanged; only the first interval's start and last interval's end move to the slot edge, and only when the scale is inset. A surface with no inset is byte-identical. Reversal: the helper returns its input.
- **J4. Period paint (item 1).** A light tint (dark and light schemes alike) or a catalogue pattern, chosen per bundle so that the decoration contrast against the ground beneath the band's centre is at least the 1.10 floor, the label meets its 4.5 floor, and the band is lighter than the plot ground on a dark scheme and a tint on a light one. Roles are declared in every bundled Theme (`period-band`, `period-label`, `period-label-chip`, with their colour bindings and an opacity token where a tint needs one). No core, schema or View change. Reversal: remove the role entries (a View that selects a period then fails with `E_THEME_ROLE_REQUIRED` as today).

### Architecture review

- **Ownership.** Layout owns every extent (`plot_bounds`, the edge extension); Scene gains no field and no role (the relation label's visual role changes from `annotation` to `text`, an existing value; Theme `annotation.fill` still paints annotation boxes); adapters are untouched. View and Domain are untouched. Theme gains content only.
- **Schema and compatibility.** No schema changes, so no schema-equivalence run. Output changes only for: surfaces whose slot exceeds their rows (overlays shorten), surfaces with relation labels (ink), surfaces with an inset scale (band cells widen into the margin), and the HALCYON period slides (paint). Each is the intended behaviour change and is listed in the slice PR. The `E_THEME_ROLE_REQUIRED` rule is unchanged.
- **Interaction with other designs.** Spec 50 section 3 (backgrounds): a period band and a closed day still sit under marks at their Theme paint order; widening a cell never changes paint order, so the overlap rules (`E_LAYOUT_BACKGROUND_OVERLAP`) see the same pairs. Closed-day cells at the edge widen by the margin only; the closed-day set is unchanged. The as-of label and member label obstacles read the as-of line extent, which now ends at the last row; no label sits below the last row.
- **Failure behaviour.** Empty plot (no rows): the slot is the plot. A margin of zero: nothing changes.
- **Gates.** The decoration contrast witness and the scene perceptibility gate read the new Scenes unchanged; `period-band` must still be painted in committed evidence (HALCYON 02, 11, 12).

## 5. Implementation plan

Each slice is one PR with `Refs #880`, merged alone, with synthetic tests that use no `examples/` input and a mutation check of each new test.

| Slice | Content | Owned files | Focused tests | Evidence |
| --- | --- | --- | --- | --- |
| S0 | This record | `docs/planning/active/issue-880-*.md` | conformance | none |
| S1 | Plot block extent for gridlines, closed days and as-of (J1); Spec 50 sentence | `surface_base.py` (`plot_bounds`), `surface_axis.py`, `surface_backgrounds.py`, `surface_composer.py`, `surface_periods.py`, Spec 50 | new unit test on a synthetic Project with slot taller than rows: overlays end at the last row; ticks and rule unchanged; no rows falls back to the slot; fill distribution unchanged | before/after PNG of Controller Z `axis-ticks` and HALCYON 04 read; 29 Scenes diffed by script |
| S2 | Relation label ink (J2) | `semantic_registry.py`, Spec 37 sentence | synthetic render with a Theme that binds `annotation.fill` to the ground: label ink equals the `text` ink and passes the contrast floor | before/after crop of `axis-ticks` read |
| S3 | Plot edge extension (J3) | `surface_geometry.py` (one helper), `surface_axis.py`, `surface_backgrounds.py`, `surface_periods.py` | synthetic Project with a milestone at the window edge: band cell, closed-day cell and period band reach the slot edge, interval starts do not move; no inset is unchanged | fresh starter before/after read |
| S4 | Period paint and roles (J4) | `src/chrona/resources/presets/bundles/*/theme.yaml` (8), `examples/halcyon-1/themes/wallboard.yaml` | test that every bundled Theme declares the three roles and that a View selecting a period renders under each bundle | HALCYON 02, 11, 12 before/after read; contrast and perceptibility gates |
| S5 | Literal acceptance review, exact-main three-OS run, close | `docs/reviews/current/issue-880-*.md` | `tools/check_issue_acceptance_reviews.py` | the run URL |

Publication boundary: S1 to S4 are independent and each leaves `main` consistent; a stop after any of them leaves nothing half-merged, and the issue records the state after each merge. Generated Scene and SVG evidence is regenerated by the derived sync, never edited.

## 6. Progress

| Slice | State | Evidence |
| --- | --- | --- |
| S0 | merged, #895 | this record |
| S1 | in review | 26 committed Scenes change, only `axis-grid`, `calendar-closed` and `as-of` bounds and points (script diff of every changed Scene); 02, 11, 12 unchanged; Controller Z `axis-ticks` and HALCYON 04 read before and after: lines now end at the ground. Ghost text is still visible in both images (S2). |
| S2, S3, S4, S5 | not started | |
