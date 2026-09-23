# Design Correction: Candidate-Label Visual Composition (#350)

**Status:** Complete — replaces post-placement visual insertion for I350R-4.

## Observed divergence

The initial I350R-4 implementation reserves width after `TextPlacement` exists.
That is sufficient for slot-owned title and table text when an explicit
available inline extent is supplied, but it cannot correctly support labels
whose bounds are chosen by the Layout candidate solver: member/plot labels,
variance labels, and annotation text. Their placement size, collision test,
fallback ladder, and wrapping must include visual advances before a candidate
is selected. Shrinking their completed text bounds afterwards would create
overlap or an artificial overflow rejection.

## Corrected Layout sequence

Layout resolves each View request to a closed asset and a target family before
any text geometry is committed. It then uses one of two composition paths:

1. **Slot text:** reserve visual advances from the slot's available inline
   extent, measure/overflow the text, and emit the resulting closure.
2. **Candidate text:** build a `VisualTextMeasure` from the target typography,
   resolved leading/trailing assets, cap height, and source text. The candidate
   solver receives its full block size (`leading advance + measured/wrapped
   text + trailing advance`) and returns a host bounds for that full block.
   Layout derives icon bounds and the text baseline inside that selected block,
   then records one shared fallback decision.

Annotation boxes similarly use the full visual-text measure when calculating
box size and leader geometry. No text visual may be added after candidate or
annotation box placement. Marks remain a separate completed-mark projection.

The shared measure contains no Scene data and no Theme object: only resolved
ratios, font metrics, asset aspect ratios, completed advances, lines, and
required/overflow policy. This keeps View occurrence selection, Context asset
closure, Theme ratio authority, Layout geometry, and Scene projection in their
published boundaries.

## Atomic implementation amendment

The currently published slot-text and mark path remains a verified intermediate
foundation, but I350R-4 cannot be declared complete until candidate labels and
annotations use the corrected pre-placement path. The target inventory commit
that introduces `note`, `group-detail`, `axis-band`, and `variance-label` must
ship only after this composition path and its direct fixture evidence are
complete; it is not an independently complete acceptance slice.

## Acceptance

- a plot label with a leading or trailing visual changes candidate bounds and
  preserves collision/fallback behavior;
- a wrapped candidate label and an annotation box measure the visual advances
  before placement;
- a no-space candidate follows its declared suppression/diagnostic policy,
  never a post-placement overlap;
- Scene receives the completed bounds unchanged, and marks retain their
  completed-mark path.
