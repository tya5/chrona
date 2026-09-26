# Prototype Evidence — Table `minmax` Content Minimum and Flex Allocation (#487)

This is evidence for the [#487 design plan](../../planning/active/issue-487-table-minmax-flex-allocation-design-plan-2026-09-26.md),
not a selected contract. It was collected from unpublished, throwaway edits to
`layout/sources.py` and `layout/engine.py` on the public base `bf98f9b0` (reverted after
each measurement; no prototype code is committed). Baseline: all 21 public materializers
reproduce byte-identical (`tools/regenerate_public_examples.py --check` passes).

## Method

A standalone script iterated the same 21 `(manifest, slide)` pairs as
`tools/regenerate_public_examples.py`, called the public materializer with `write=False`,
and for each slide recorded: whether the generated Scene/SVG matched the committed
evidence, the `table` slot's `inlineSize`, and the top-level `diagnostics` list. Three
configurations were run in isolation (each reverted with `git checkout --` before the
next):

- **Baseline** — `main` unchanged.
- **Candidate A** — `measure_sources`'s `table` branch sets `minimum_inline` to the
  measured column+gutter extent (`_table_content_inline`, the same measure `preferred_inline`
  already uses since #480) instead of `min(column_floor, widest_row_label)`.
  `engine.py::_allocate` is unchanged (additive: `size = minimum + remaining × weight ÷
  total_weight`).
- **Candidate A+B** — the same `minimum_inline` fix, plus `_allocate` changed to CSS
  Grid's `max(minimum, share)`, where `share = free × weight ÷ total_weight` and `free`
  is the available space minus the sizes already assigned to non-flexible tracks (i.e.
  the flexible tracks' own minimums are excluded from the space `share` is computed
  over, not just from what remains after subtracting them).
- **Isolation check (B only)** — `_allocate` changed to `max(minimum, share)` with
  `minimum_inline` left at its current, too-small value.

## Corpus impact: which slides change

| Configuration | Materializers changed (of 21) |
| --- | --- |
| Candidate A (minimum fix, additive allocation) | 18 |
| Candidate A+B (minimum fix, `max(min, share)` allocation) | 18 — **the same 18** |
| Isolation check (allocation change alone, old minimum) | 18 — **the same 18 again** |

The unaffected 3: `halcyon-1/overlay-briefing` uses `inlineSize: content` (no `minmax`,
so `minimum_inline` is unused for sizing — its used size is always `preferred_inline`),
and 2 slides have no `table` source at all.

The isolation check shows the allocation-semantics choice is orthogonal to, but not
independent in effect from, the minimum-inline fix: **any** nonzero `minmax` minimum
already produces a different number under the two rules, whether or not the minimum
value itself is corrected. In the public corpus, table slots are the only flexible
tracks with a nonzero `minmax` minimum — every other `fill`/`{fr: n}` track has
`minimum == 0`, where `max(0, share) == 0 + share`, so the two allocation rules coincide
exactly and produce identical numbers. Switching the engine's allocation rule therefore
cannot change any non-table flexible track in the current corpus; the blast radius is
exactly the nine table layouts already identified in the #480 evidence.

## Corpus impact: by how much

Table slot `inlineSize`, baseline vs. each candidate (px; delta from baseline in
parentheses):

| Slide | Baseline | Candidate A (additive) | Candidate A+B (`max(min,share)`) |
| --- | --- | --- | --- |
| aster-ssd/overview | 542.4 | 599.9 (+57.5) | 458.4 (−84.0) |
| controller-z-ja/executive | 542.4 | 681.9 (+139.5) | 458.4 (−84.0) |
| controller-z/annotations | 542.4 | 606.3 (+63.9) | 458.4 (−84.0) |
| controller-z/composition-compact | 549.6 | 613.5 (+63.9) | 465.6 (−84.0) |
| controller-z/elevated | 542.4 | 606.3 (+63.9) | 458.4 (−84.0) |
| controller-z/executive | 542.4 | 606.3 (+63.9) | 458.4 (−84.0) |
| controller-z/icons | 542.4 | 606.3 (+63.9) | 458.4 (−84.0) |
| controller-z/material-icons | 542.4 | 595.8 (+53.4) | 458.4 (−84.0) |
| controller-z/plan-only | 542.4 | 567.2 (+24.8) | 458.4 (−84.0) |
| halcyon-1/flight-readiness | 921.2 | 1051.7 (+130.5) | 823.6 (−97.6) |
| halcyon-1/gallery-dark | 789.4 | 1059.5 (+270.0) | 699.0 (−90.4) |
| halcyon-1/gallery-mono | 789.4 | 1059.5 (+270.0) | 699.0 (−90.4) |
| halcyon-1/launch-campaign | 698.0 | 823.1 (+125.1) | 631.2 (−66.8) |
| halcyon-1/mission-brief | 789.4 | 1059.5 (+270.0) | 699.0 (−90.4) |
| halcyon-1/overlay-briefing | 630.0 | 630.0 (+0.0) | 630.0 (+0.0) |
| halcyon-1/programme-board | 410.5 | 557.7 (+147.2) | 383.8 (−26.7) |
| halcyon-1/replan-baseline | 389.5 | 567.2 (+177.7) | 395.5 (+6.0) |
| halcyon-1/tvac-slip | 389.5 | 511.2 (+121.7) | 327.0 (−62.5) |
| orion-asic/gates | 609.8 | 769.7 (+159.8) | 458.4 (−151.4) |

`halcyon-1/mission-brief`'s 789.4 → 1059.5 px under additive allocation matches the
number already cited in the [#480 prototype evidence](issue-480-table-and-row-metrics-prototype-evidence-2026-09-26.md)
for the same corrected-minimum-plus-additive-allocation combination, confirming the two
measurements agree across sessions.

Under additive allocation (Candidate A), every changed table **grows**, by 24.8–270.0 px,
because the correction can only add to the existing `minimum + share` sum. Under
`max(minimum, share)` (Candidate A+B), 17 of the 18 changed tables **shrink** relative to
today's published width, by 26.7–151.4 px, because the corrected minimum is usually larger
than the track's `fr` share and so replaces the old `minimum + share` sum rather than
extending it; `halcyon-1/replan-baseline` is the one exception, growing 6.0 px, because its
`fr` share exceeds even the corrected minimum there. In all cases the resulting size is,
by construction, never less than the measured columns and gutters — Candidate A+B does
not violate acceptance criterion 1, it just does not add anything beyond the minimum
unless the `fr` share independently earns more.

## Corpus impact: diagnostics

| Slide | Candidate A | Candidate A+B |
| --- | --- | --- |
| controller-z-ja/executive | adds `I_LAYOUT_PLOT_LABELS_SUPPRESSED` (count=1), `W_LAYOUT_LABEL_SUPPRESSED:member-label:ga:ga` | none |
| controller-z/annotations | adds `W_LAYOUT_NOTE_INDEX_SUPPRESSED:evb-highlight` | adds `W_LAYOUT_NOTE_INDEX_SUPPRESSED:performance-note`; removes the plot-label/member-label pair above |
| controller-z/composition-compact | none | adds `W_LAYOUT_RELATION_LABEL_SUPPRESSED:relation:bringup-to-performance:…`; removes the plot-label/member-label pair |
| controller-z/elevated | none | same as composition-compact |
| controller-z/executive | none | same as composition-compact |
| controller-z/icons | none | removes the plot-label/member-label pair (no new warning) |
| halcyon-1/gallery-dark | none | adds `I_LAYOUT_PLOT_LABELS_SUPPRESSED` (count=1), `W_LAYOUT_LABEL_SUPPRESSED:member-label:payload-tvac:payload-tvac` |
| halcyon-1/gallery-mono | none | same as gallery-dark |
| halcyon-1/launch-campaign | adds `I_LAYOUT_PLOT_LABELS_SUPPRESSED` (count=4) and 4 `W_LAYOUT_LABEL_SUPPRESSED:member-label:*` | none |
| halcyon-1/mission-brief | none | same as gallery-dark |
| halcyon-1/replan-baseline | none | removes `W_LAYOUT_AXIS_DENSITY` and 3 `W_LAYOUT_AXIS_LABEL_THINNED` (the table's small +6.0 px growth leaves more room for the axis) |
| halcyon-1/tvac-slip | adds 2 `W_LAYOUT_RELATION_LABEL_SUPPRESSED:relation:*` | adds 1 of the same 2, removes a different (`relation:psr-shipment:…`) |

Neither candidate is warning-free. Candidate A's new warnings come from the wider table
crowding its sibling plot/relation surface; Candidate A+B's come from the narrower table
giving that sibling surface *more* room, which can also relabel or resuppress a
different member/relation once its available width changes. Both are legitimate,
attributable consequences of the corrected minimum, not defects in either allocation
rule; each must still be reviewed slide-by-slide in the implementation slice, per
`AGENTS.md`.

## `print-mono` dependency

`docs/research/presentation/preset-tuning/print-mono/README.md` records that the preset
gives the table slot `minmax: {min: content, max: {fr: 1}}` specifically to work around
the #480 content-sizing gap (a plain `inlineSize: content` table had no slack for its own
last column). `halcyon-1/gallery-mono` and `halcyon-1/launch-campaign`, both `print-mono`
slides, are in the 18-slide changed set above under every candidate.

## What this does not decide

This evidence does not choose between the two allocation rules; it only measures their
effect so the design (`issue-487-table-minmax-flex-allocation-design-2026-09-26.md`) can
choose deliberately, as the issue's second acceptance criterion requires.
