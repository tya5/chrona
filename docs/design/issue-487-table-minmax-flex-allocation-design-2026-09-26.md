# Design — Table `minmax` Content Minimum and Flex Allocation (#487)

**Status:** approved for implementation, with a same-day amendment to Contract 2 (below):
the architecture review's `max(minimum, share)` formula oversubscribed `available`; the
lead required CSS Grid's iterative "find the size of an fr" resolution instead before
phase-2 code. **Plan:** [design plan](../planning/active/issue-487-table-minmax-flex-allocation-design-plan-2026-09-26.md).
**Evidence:** [prototype evidence](../research/presentation/issue-487-table-minmax-flex-allocation-prototype-evidence-2026-09-26.md).
**Authorities:** Specifications 24 §2.1, 33 §5; [ADR-0032](../decisions/ADR-0032-flexible-track-minimum-is-a-floor.md); the [#480 design](issue-480-table-and-row-metrics-design-2026-09-26.md), which fixed `inlineSize: content` only and filed this issue for `minmax`.

## Use case

An author gives the table slot `inlineSize: {minmax: {min: content, max: {fr: N}}}` so
the table never crowds its own columns and still grows with the timeline's spare width.
The slot is never narrower than the table's measured columns and gutters, and the
allocator's meaning of "minimum" is stated, not implied by whichever arithmetic the
engine happens to run.

## Contract 1: `min: content` is the table's measured content

**Owner: Layout.** `layout/sources.py::measure_sources`'s `table` branch sets:

```
minimum_inline = _table_content_inline(value.table, ...)   # when value.table has columns
preferred_inline = max(column_floor, minimum_inline)         # unchanged from #480
```

- `minimum_inline` is exactly the measure `preferred_inline` already uses since #480
  (`_table_content_inline`: natural column widths, hierarchy indent, and gutters). No new
  measurement function is added; this closes the gap between the two by reusing the one
  #480 already built.
- `preferred_inline ≥ minimum_inline` always holds by construction (`preferred_inline` is
  a `max` over the same quantity), so `minimum_inline` can never exceed the slot's
  preferred size.
- When `value.table` has no columns (a table source declared with zero `tableColumns`,
  which the schema still permits), `minimum_inline` falls back to today's
  `min(column_floor, text_inline)`, unchanged, because there is no column content to
  measure. This case does not occur in the public corpus.
- `table.column.minInlineSize` keeps its #480 meaning: a per-column floor folded into
  `preferred_inline` via `column_floor`. It is not part of `minimum_inline`, which answers
  a different question ("how small can this legitimately get") from `preferred_inline`
  ("how large should this get by default").

## Contract 2: a flexible track's `minmax` minimum is a floor, not an addend

**Owner: Layout.** `layout/engine.py::_allocate` changes its flexible-track distribution
from additive to CSS Grid's "find the size of an fr" algorithm, not a single-pass
`max(minimum, share)` per track.

**Amendment (this document, 2026-09-26):** the design's first draft specified a single
pass — compute one `share_i` per flexible track from the whole free space, then take
`max(minimum_i, share_i)` for each. The lead's review of the phase-1 report identified
that this **oversubscribes `available`**: when one track's minimum exceeds its share, it
takes its minimum while every *other* flexible track still takes its own uncorrected
share (computed as if that track had taken only its smaller share), so the sizes can sum
to more than `available` — silently growing the canvas or overflowing a sibling, exactly
the failure Contract 2 exists to prevent. The corrected algorithm resolves this
iteratively, matching CSS Grid's own `fr`-track resolution:

```
sizes[i] = target_i  for every non-flexible track (weight_i == 0)      # unchanged
leftover = available − sum(those sizes)
flexible = {i : weight_i > 0}
loop:
    if flexible is empty: stop
    fr = leftover / Σ(weight_i for i in flexible)          # 0 if leftover <= 0
    violators = {i in flexible : minimum_i > fr × weight_i}
    if violators:
        for i in violators: sizes[i] = minimum_i; leftover −= minimum_i
        flexible −= violators; continue loop
    clamped = {i in flexible : maximum_i is not None and maximum_i < fr × weight_i}
    if clamped:
        for i in clamped: sizes[i] = maximum_i; leftover −= maximum_i
        flexible −= clamped; continue loop
    for i in flexible: sizes[i] = fr × weight_i             # stable: no violators, no clamps
    stop
```

- **Each round recomputes `fr` over the shrinking flexible set and the shrinking
  `leftover`.** A track whose minimum exceeds its share at the *current* `fr` is frozen at
  that minimum and removed from the set; `leftover` is reduced by exactly that minimum, so
  the remaining tracks' next `fr` is computed over what is actually left, not the original
  pool. This is what keeps `Σ sizes == available` whenever every flexible track's minimum
  fits (`Σ minimum_i ≤ available`): every unit of `available` is assigned to exactly one
  track, either as a frozen minimum/maximum or as a share of what nothing else has claimed.
- **A finite `maximum` is resolved the same way**, in a second check each round (after
  minima are stable): a track whose share would exceed its `maximum` is frozen at that
  maximum instead, and the freed surplus is redistributed to the remaining tracks by the
  same re-loop. (The current `_spec_base` dispatch cannot actually produce a flexible
  track with a finite `maximum` through the public Layout Profile grammar — every spec that
  yields a nonzero weight, `fill` or `{fr: n}`, also yields an unbounded maximum — so this
  path is forward-compatible rather than reachable today; it is still implemented and
  tested directly, per CSS Grid's own algorithm, rather than left as a latent gap.)
- **If every flexible track's minimum together still exceeds `available`** (`Σ minimum_i >
  available`), the loop freezes every one of them at its minimum and `flexible` empties
  with `leftover` negative; `Σ sizes` then exceeds `available`, exactly as an
  under-sized valid profile already produces today (the caller's existing typed
  `W_LAYOUT_VISIBLE_OVERFLOW`/canvas-completion path is unchanged and still applies).
- A track whose `minmax` minimum is `0` (`fill`, plain `{fr: n}`) is numerically
  unaffected by any of this: with `minimum_i == 0`, it can never be a violator
  (`0 > fr × weight_i` is false whenever `fr ≥ 0`), so it always reaches the final,
  single-pass `fr × weight_i` assignment — identical to the pre-#487 additive result
  (`0 + share == share`). The prototype's isolation check (design plan, item 3) and a
  dedicated unit test (implementation plan) confirm this holds for every non-table
  flexible track in the public corpus.
- This is the standards-aligned reading of `minmax`/`fr`: CSS Grid's own `fr` tracks
  resolve by this same iterative "find the size of an fr" procedure, and Specification 33
  §5 already names these keywords with the implication that they behave the way CSS Grid
  authors expect. Keeping the current additive rule would leave that vocabulary silently
  divergent from its own naming; a single-pass `max(minimum, share)` would leave it
  divergent in a different, more dangerous way (oversubscription).
- **Migration is deliberate and disclosed**, not incidental: see the re-measured evidence.
  Under this rule, 17 of 18 affected public tables **shrink** below today's published
  width, because the corrected minimum usually already exceeds the small `fr` share those
  slots were given; one (`halcyon-1/replan-baseline`) grows slightly. This is accepted: the
  rule guarantees the minimum and nothing more, so a slot given a small `fr` share should
  not use the minimum-correction as a channel to also grow well past what its own share
  earns. An author who wants the table wider than its measured content raises its `fr`
  weight or its `max`, not its `min`.

## Why not keep additive allocation

Keeping the current additive rule together with the Contract 1 fix satisfies acceptance
criterion 1 alone, but it reproduces exactly the growth pattern the issue's own summary
names as the defect: "the flexible share adds on top of the minimum... widens the table
by roughly the whole difference," taking that space from the sibling track (usually the
timeline) on every corrected slide (+24.8 to +270.0 px in the evidence). Choosing additive
deliberately would still meet the letter of criterion 2 ("the meaning is specified"), but
it would specify the meaning the issue was filed to question, without any offsetting
benefit — the isolation check shows switching to the iterative rule does not cost any
additional public byte change beyond what raising the minimum already causes, since
exactly the same 18 slides move either way.

A single-pass `max(minimum, share)` (this document's first draft, corrected above) is also
rejected on its own: it is not the CSS Grid algorithm it claims to follow, and it
oversubscribes `available` whenever more than one flexible track's minimum needs
correcting relative to its share, which is precisely the situation #487 introduces on 18
public slides. The iterative resolution costs nothing extra in code complexity that
matters (one bounded `while` loop, at most one pass per track) and is the only one of the
three options that keeps `Σ sizes ≤ available` whenever the profile's minima allow it.

## Migration and compatibility

- No schema change. `minmax`, `min`, `max`, `fr` keep their existing spelling;
  Specification 33 §5's "remaining space" wording is amended to state the used-size
  formula precisely (below), not to add a keyword.
- No Theme, View, or metric-name change. `table.column.minInlineSize` is unchanged.
- **Specification 24 §2.1** gains one sentence: `minmax: {min: content}` on the table slot
  uses the same measured content extent as `preferred_inline`, so the slot's minimum is
  never smaller than its columns and gutters.
- **Specification 33 §5** gains the used-size resolution for a flexible track: the
  iterative "find the size of an fr" procedure above, not a single-pass formula. This is a
  normative change to every `minmax`-with-nonzero-minimum flexible track in the engine,
  not only tables, so it is also recorded as
  [ADR-0032](../decisions/ADR-0032-flexible-track-minimum-is-a-floor.md).
- **Public evidence:** 18 of 21 materializers change (see the re-measured evidence for the
  exact byte impact per slide, superseding this document's earlier draft numbers, which
  were measured under the rejected single-pass formula). This is regenerated and attributed
  in one batch per implementation slice; before/after PNGs of HALCYON `01-mission-brief`,
  `orion-asic/gates`, and `09-gallery-mono` were rendered and inspected in the phase-2
  slice — table text stays intact and legible at every corrected width, and the freed
  space visibly reaches the sibling timeline/plot surface. No slide gained a
  `W_LAYOUT_VISIBLE_OVERFLOW` it did not already have.

## Diagnostics

No new diagnostic. Existing `W_LAYOUT_LABEL_SUPPRESSED`, `W_LAYOUT_RELATION_LABEL_SUPPRESSED`,
`W_LAYOUT_NOTE_INDEX_SUPPRESSED`, `I_LAYOUT_PLOT_LABELS_SUPPRESSED`, and axis-thinning
diagnostics may newly appear, disappear, or move to a different member/relation as the
table's corrected width changes how much room its sibling surface has. Each occurrence
must be attributed to the width change in the slice review, not silently accepted.

## Tests

- A `minmax: {min: content, max: {fr: 1}}` table slot's `minimum_inline` equals
  `_table_content_inline`'s result for a fixture with multiple columns and a hierarchy
  cell (reusing the #480 fixture where practical).
- A table source with zero columns keeps today's `min(column_floor, text_inline)`
  fallback.
- The flexible-track resolution (`_resolve_flexible_tracks`, the pure bases-to-sizes step
  `_allocate` delegates to): a track whose minimum exceeds its share is frozen at exactly
  that minimum, and the sibling track's redistributed share brings the total to exactly
  `available` (not more) — the direct regression guard for the oversubscription bug this
  amendment fixes.
- The same function with a track whose finite maximum is smaller than its share: frozen
  at that maximum, with the surplus redistributed and the total still exactly `available`.
  (Exercised directly, since the public grammar cannot produce a flexible track with a
  finite maximum today — see Contract 2.)
- The same function with every flexible track's minimum at `0`: identical output to the
  pre-#487 additive formula (regression guard for the isolation-check finding).
- The same function with the flexible tracks' minima summing to more than `available`:
  every track keeps its minimum and the total exceeds `available`, matching the existing
  typed-overflow completion path.
- An end-to-end `solve_layout` test through the public `minmax: {min: {fixed: …}, max:
  {fr: 1}}` grammar, confirming the min-exceeds-share case is reachable and correct
  through the whole engine, not only the internal function.
- A CLI render of one public layout under both the old and new rule, asserting the exact
  before/after widths recorded in the evidence, as a golden regression guard for the
  deliberate migration.
