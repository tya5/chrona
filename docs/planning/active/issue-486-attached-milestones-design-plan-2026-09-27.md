# Design Plan — Attached Milestones (#486)

**Public base:** `e3560ad9` on `main`. **Source of truth:** [Issue #486](https://github.com/tya5/chrona/issues/486); Specification 05 §4.4 (`parent` is the sole containment edge) and §9 (`deadline` is not a scheduling bound); #440 (`points: predecessor` fold); #464 (gate glyphs); #467 (lane rows, in progress).

## Published baseline

- A point object cannot say which task it belongs to. `parent` carries the WBS, and relations carry scheduling logic.
- In automatic rows, every point takes its own row unless the View sets `rows.points: predecessor`. That fold infers a host from a single incoming relation from a span (`projection.py`, `_fold_automatic_points`), and moves the point onto the host row as a `shared`-track member.
- A shared-track member is a normal row member: Layout places its mark on the host row, and member labels already exist for multi-member rows.
- No committed example has a long task with points inside it.

## Literal acceptance ledger

1. “The Project schema accepts `attachesTo` on point objects; the validation errors and the outside-span warning are covered by tests.”
2. “Attachment changes no scheduled date. A test compares schedules with and without it.”
3. “A View draws an attached milestone on its host's row, both with and without #467 lanes, and `points: own-row` restores its own row.”
4. “The milestone's name and date stay visible, and its delta if it has one.”
5. “One committed example has a long task with at least two intermediate milestones attached. HALCYON-1's `campaign` or `mcs` would serve.”

## Questions for the design

- Does `attachesTo` bump the Project version, or extend v0.7 in place?
- How does a View opt out, given that `own-row` is already the default of `rows.points`?
- How does the name and date stay visible without new label vocabulary?
- Which example carries the evidence, and what does it do to the corpus?

## Sequencing

Data validation (row 1–2) and automatic-row placement (rows 3–4 without lanes) do not depend on #467. Placement on a lane (row 3 with lanes) consumes #467's allocator and lands after #467 L3. The View change shares the next free View version with #479 when they land together.
