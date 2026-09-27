# Design Plan — Milestone-Only Rows and Fold Policies (#440)

**Public base:** `76ffe2e4` on `main`. **Source of truth:** [Issue #440](https://github.com/tya5/chrona/issues/440); #278 (fold policies); #467 (lane rows: collision allocator, lanes as the default); #486 (attached points and their required label); #434 (`fill` distribution, landed); #400 (silent loss).

## Published baseline

- `rows.points` is `own-row | group-header | predecessor`, and #486 adds `attached` as the new default.
- **`group-header`** stacks the folded points of a group by index (`surface_composer.py`, `track_index`). The overflow is now a `W_LAYOUT_GROUP_HEADER_OVERFLOW` that grows the header, not a refusal. Three points in `launch` still take three tracks, whatever their dates.
- **`predecessor`** moves a point onto its single span predecessor's row. Its label follows the View's optional-label policy and can be suppressed, so the name is lost.
- **No key-milestone row** exists.
- **`fill`** renders since #434, but no folded slide uses it.
- #467 L2 provides `allocate_lanes`: a deterministic, collision-aware allocator over measured mark and title footprints, with a label ladder that never suppresses a name.

## Literal acceptance ledger

1. “`02-programme-board` renders with `points: group-header`, and the `launch` group's three milestones share one lane.”
2. “On every committed slide, no folded milestone is left without a visible name.”
3. “`points: key-row` exists, and one committed slide uses it with every milestone labelled.”
4. “No committed slide has more than a quarter of its rows holding only a milestone, unless the view declares `own-row` with a reason.”
5. “One committed folded slide also uses a distribution that does not leave the freed height empty.”

## Sequencing

Everything here consumes #467's allocator and its lane Views. Row 4 is measured on the corpus after #467 moves slides to lanes. The View changes share the next free View version with #479 and #486. The design is written now; implementation starts when #467 L3 lands.
