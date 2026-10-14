# Issue #440 — smallest fix for the two fold policies (design note, 2026-10-14)

Status: proposal. Refs #440. Board #454 has #440 in backlog P6; this note
does not reopen priority. It records the smallest slice so a successor does
not need the 2026-09-27 set (`docs/design/issue-440-point-folds-design-2026-09-27.md`),
which also bundles `key-row`, fallback lists and a corpus bound.

## Baseline on main (7b4796e79)

- `surface_marks.py` (folded-point loop, ~l.278-310) gives each folded point
  of a group track `track_index` in date order, with `occupied = n * pitch`.
  The header grows when `occupied` exceeds it and
  `W_LAYOUT_GROUP_HEADER_OVERFLOW` is recorded (`surface_completion.py`).
  The `E_LAYOUT_GROUP_HEADER_OVERFLOW` refusal quoted in the issue is no
  longer in `src/`; the index stacking it described remains. Verified by grep.
- `_fold_automatic_points` (`projection.py`) `predecessor` moves a point onto
  the row of its single span predecessor as a shared-track item and drops the
  point's own row. `attached` (#486) does the same through `attachesTo`.
- No `allocate_lanes` exists on main (grep). #467 lanes is a different
  mechanism (`lane_projection.py`).

## (a) Collision lanes for group-header folds

Rule: within one group, sort folded points by (date, object id) and assign
each to the lowest lane whose last occupied x-extent end is at or before the
point's start (greedy interval packing). Extent = mark footprint plus the
measured title label width plus the existing label gap, on the side the
label is placed. Lane count = lanes used. `occupied = lanes * pitch`.
Refusal: none new. A packed result taller than the header uses the existing
header-growth path and `W_LAYOUT_GROUP_HEADER_OVERFLOW`; that is the only
"does not fit" outcome, and it now fires only when packing needs more lanes
than the header holds.

Basis: greedy packing in start order is optimal for interval graphs, so no
packing with fewer lanes exists for the chosen extents. Files: the folded
loop in `surface_marks.py`; the label width comes from the existing label
measurement, not a new one. Local defect in one owner: fast path, one PR,
no schema change.

## (b) `predecessor`: leave as is, with one narrow guard

`predecessor` is opt-in and its folding is the author's explicit choice. The
loss named in the issue (table row, dates, suppressed label) is a
visibility problem already covered by #486's required `attached_labels`
composition (`lane_label_intent.py`, `surface_member_labels.py` read it
today). Proposed: do not change the fold; require that a folded point's
title and planned date are carried by that label composition, and fail
visibly (not `W_LAYOUT_LABEL_SUPPRESSED`) when it cannot be placed. If that
composition already applies to `predecessor`, the row is a test only. This
is unverified here and must be checked first by the implementer.
`key-row`, fallback lists and the 25% corpus bound are out of this slice;
#467 lanes and #486 `attachesTo` cover the target slides.

## Acceptance rows and basis

| # | Row | Basis |
|---|---|---|
| 1 | Three group-header points at x=1101, 1716, 1740 with labels share lanes by collision: the first and last two are 600 px apart, so lane count is at most 2 and the first lies in lane 0 with a non-colliding neighbour | Issue #440 coordinates; greedy packing rule above |
| 2 | Two points whose extents overlap never share a lane | Definition of collision; synthetic fixture |
| 3 | Lane count equals the clique number of the extent overlaps (no avoidable extra lane) | Interval-graph optimality of greedy start-order packing |
| 4 | Header grows and `W_LAYOUT_GROUP_HEADER_OVERFLOW` is recorded only when packed lanes exceed header capacity | Existing path in `surface_completion.py` |
| 5 | A folded `predecessor` point has its title and planned date in a label or the fold is not applied | Issue #440 "folded milestone keeps its name"; #486 composition |
| 6 | No example file changes; any rendered difference is reported as counts in the PR | AGENTS.md "never absorb a side effect by editing examples" |

Not claimed: any render-time or size gain. No profile exists.

## Open for the owner

Whether row 5 should refuse the fold or keep it with a visible overflow
label. Recommendation: visible overflow label, matching the 2026-09-27
design and #488's rule that labels stay in their own band.
