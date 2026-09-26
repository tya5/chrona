# Slice Review — I488-1 Member Labels in Their Own Row Band (#488)

**Design:** [#488 design](../../design/issue-488-member-label-row-band-design-2026-09-27.md). **CI:** pending.

## Change

`surface_composer.py` passes each member label's row band as its placement `bounds`, extended by any chip padding. `place_label` already enforced `bounds` on every candidate, including the side-neighbourhood search, so no search code changed.

## Evidence attribution

Seven public slides change. Every changed primitive is a member label or a variance label that negotiates against the member labels. No mark, row, axis or relation primitive changed.

| slide | member labels moved into their row | newly suppressed member labels | other primitives |
| --- | --- | --- | --- |
| `aster-ssd/overview` | 7 | — | unchanged |
| `halcyon-1/01-mission-brief` | 7 | — | unchanged |
| `halcyon-1/03-launch-campaign` | 2 | — | unchanged |
| `halcyon-1/04-tvac-slip` | 5 | — | unchanged |
| `halcyon-1/07-replan-baseline` | 1 | `integration` (counted) | `variance:integration` and `variance:vibration` re-placed around the moved labels |
| `halcyon-1/08-gallery-dark` | 7 | — | unchanged |
| `halcyon-1/09-gallery-mono` | 7 | — | unchanged |

The before and after crops of `01-mission-brief` were compared. Labels that used to float above their bars into the previous row (`Bus functional test`, `Critical design review`, `Pre-ship review`, `Flight readiness review`, `Launch window opens`, `LEOP and commissioning` and `First light`) now sit on their own row, at the bar's start or end.

## Tests

- **Default draft.** `test_default_draft_guides_every_bar_across_the_plot_and_names_it_at_its_end` now asserts the #488 rule on the HALCYON-1 default draft. Every visible member label sits inside its row band, at its bar's end or start. The count is 24 visible plus 4 suppressed, out of 29 selected items. `optics`, `bus-test` and `cdr` are suppressed, because the end, the start and the in-row neighbourhood are all crossed by dependency strokes. `payload-tvac` was already suppressed before.
- **Suppression counts.** The two suppression-count tests now derive the expected count from the per-label diagnostics, so they no longer hard-code a number.
- **Chips.** The label-chip test uses a 0.1 em chip padding. Controller Z's labels sit just above their bars, and a 0.4 em chip lifted the text out of the row.
- **Results.**
  - Full suite: 1304 passed.
  - `regenerate_public_examples --check`: PASS.
  - Scene perceptibility: PASS.
  - `conformance/run_conformance.py`: PASS.
