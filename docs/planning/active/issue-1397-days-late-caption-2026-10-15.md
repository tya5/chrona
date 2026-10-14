# #1397 row 3: "days late" caption beside the deadline run

Status: design note, 2026-10-15. Base: `origin/main` 3ce47886d. Refs #1397. Outcome: **stopped before code**;
the row cannot be a pure figure-vocabulary binding. Question and recommendation are on the issue.

## Literal row

"A 'days late' caption next to the run, through the #586 figure vocabulary and its format rules (locale and unit
word are author text). `W_DEADLINE` already states the number."

## Baseline (verified on main)

- Figures are resolved once per render (`scope: global`) or once per group (`scope: group`)
  (Spec 06 section 7.2, `src/chrona/core/figures.py`). There is no per-object scope.
- Facts are `asOf`, period side, `{object, endpoint: at|start|end}`, and `{group: firstPlannedStart}`. There is no
  `deadline` fact, so `daysUntil` cannot express "finish minus deadline"; the late count lives only in
  `deadline_statuses` / `W_DEADLINE` (`src/chrona/core/deadlines.py`).
- `figureFormats` targets `count` figures only. A day figure has no closed format, so "through the format rules"
  has nothing to select for a late-day figure today. Unit word and locale come from the template text.
- Template consumers: period labels, headings, slot captions (Spec 06 section 7.2). A deadline mark is none of
  them, and Spec 06 section 7.3 states "No text is drawn" for it.
- `compose_deadline_marks` (`surface_deadlines.py`) emits only tick and run `Path` shapes.

## Why it is not a pure binding

A caption per deadline needs three things that do not exist, and the second and third are mark geometry:

1. A per-object figure (new scope, or a `deadline`/`finish` object fact plus per-object resolution). This
   is a Core figure-vocabulary change (Spec 05 section 12.2), not a binding.
2. Text placement beside the run: measurement, anchor (run end vs. midpoint), side, overflow at the plot
   edge, and collision with the planned mark, labels and other ticks. Spec 50 owns label-versus-mark gates;
   the run's host row is mark geometry (dev A area).
3. A new Scene text primitive owned by the deadline decoration, a Theme text role for it (Theme must
   declare one, or the caption borrows an unrelated role), and legend/attribution identity.

Splitting it as "the figure part only" delivers nothing visible, so no slice is publishable alone.

## Recommendation

Do the figure part and the placement as one dev A-owned slice, with these choices:

- View: `deadlines: {show, caption: {template: "{daysLate} d late"}}`, with one closed placeholder
  `{daysLate}` (signed calendar days, the `W_DEADLINE` number) instead of a general per-object figure scope.
  Optional member, additive in v0.28 (Spec 56 section 3.2); absent member changes nothing.
- Format: an optional `format` reusing the closed `figureFormats` forms (`digits`, `english-words`, `kanji`,
  `kanji-formal`) for the number; unit word and locale are template text, as the row says.
- Placement: caption starts at the run end plus a gap, vertically centred on the run's tick row; if it does
  not fit before the plot edge it goes on the other side of the tick; a still-colliding caption is dropped with
  a counted `I_LAYOUT_DEADLINE_CAPTION_DROPPED`, never silently.
- Theme: reuse the existing `deadline-mark.stroke` ink for text only if it keeps 3:1 on the row ground,
  otherwise require a text role (`E_THEME_ROLE_REQUIRED`).
- Only slipped deadlines get a caption; kept deadlines (`show: all`) do not.

Acceptance rows once taken up: the caption shows the late-day count through the template and format;
an absent member renders byte-identically; a kept deadline has none; an overflowing caption is placed on the
other side or dropped with the counted diagnostic.
