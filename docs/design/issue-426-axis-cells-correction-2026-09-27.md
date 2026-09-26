# Design Correction — Axis Lanes, Cells and Rule (#426, rows 5–10)

**Corrects:** the [#426 design](issue-426-axis-tier-appearance-design-2026-09-26.md), which covered acceptance rows 1–4 only. The issue body was extended (by the reviewer at `e907ac47`) with rows 5–10 before #426 closed; it was reopened. **Evidence:** the table "What the design targets expect of the axis" in the issue body, measured on `mission-light`.

Every new capability is a Theme declaration, so no View version is needed. A Theme without the new declarations renders exactly as today, byte for byte.

## Row 5 — a labels tier has a lane, and its label is centred in it

- A labels tier's typography role (`axis`, or the role named by `typographyRole`) may declare `laneBlockSize`, a number token in px. That tier is then a **declared lane**: its block size is exactly `laneBlockSize`, lanes stack from the top of the axis slot in labels-tier order, and each label's line box is **centred** in its lane (the #480 cell rule: box top = lane top + (lane − line block) / 2; baseline = box top + font size).
- A band tier whose `unit` equals a declared-lane labels tier's unit fills **exactly that lane**, whatever the number of band tiers.
- A tier without `laneBlockSize` keeps today's stacking. A View whose tiers declare no lanes keeps today's band rule (the single band spans the slot; several bands stack, #426 rows 1–4).

## Row 6 — cell boundaries

- The band tier's Theme role may declare `cellGap` (number token, px). Each band cell is then inset by `cellGap / 2` at both inline ends, leaving a visible gap between cells.
- A Theme may bind the role `axis-cell-separator` (stroke, `strokeWidth`, optional `dash`). Layout then draws one Path at each interval start inside the axis slot, except the first. Separators span the lane of every declared-lane tier whose interval starts there, or the whole slot when no lanes are declared.
- Per-cell outlines already exist: `backgroundTreatment: outline` on the band role.

## Row 7 — the axis rule

A Theme may bind the role `axis-rule` (stroke, `strokeWidth`). Layout then draws one Path along the bottom edge of the axis slot, across the timeline's inline extent. **Every shipped Theme binds it** (the 10 corpus Themes and 5 bundle Themes, at `strokeWidth` 1, in `text` or the Theme's axis ink), so all public evidence gains one `axis-rule` primitive. This is intended.

## Row 8 — inset for start-aligned labels

An axis label role may declare `labelInset`: a ratio of that role's font size. A start-aligned label is placed at `cell start + labelInset × font size`; its available width shrinks by the same amount. Centred labels are unchanged.

## Row 9 — the catalogue presets

The five bundle Themes and Views adopt all of the above:
- **View:** a quarter band, a month band, quarter labels (`typographyRole` naming a distinct emphasis role) and month labels, all centred.
- **Theme:** `laneBlockSize` on both axis label roles, `cellGap` on the band roles, an `axis-cell-separator` binding, `axis-rule`, and `labelInset`.

A test renders HALCYON-1 with each preset. It asserts:
- two label lanes, with every label's box centred in its lane;
- bands filling exactly their lanes;
- gaps between cells;
- separators at interval starts;
- an axis rule at the axis bottom.

## Row 10 — optional expectations

- Alternating fills are [#490](https://github.com/tya5/chrona/issues/490).
- Cell corner shape (Sunday Strip, Off-World), short ticks (Swiss Grid, Flat Pack, Off-World) and two labels in one cell (Title Card, Tenth Frame) are filed as follow-up issues naming those targets.

## Ownership

- Theme declares; Layout completes lane geometry, centring, insets and cell, separator and rule paths.
- The semantic registry gains `axisRule` and `axisCellSeparator` (line purposes).
- Scene projects Paths and Rects; the adapters are unchanged.
