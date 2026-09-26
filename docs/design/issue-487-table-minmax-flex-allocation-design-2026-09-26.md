# Design — Table `minmax` Content Minimum and Flex Allocation (#487)

**Status:** proposed for whole-architecture review. **Plan:** [design plan](../planning/active/issue-487-table-minmax-flex-allocation-design-plan-2026-09-26.md).
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
from additive to CSS Grid's `max(minimum, share)`:

```
non_flex_total = sum(sizes[i] for i where weight_i == 0)   # fixed/intrinsic tracks, already resolved
free = available - non_flex_total
for i where weight_i > 0:
    share_i = free * weight_i / total_weight
    sizes[i] = max(minimum_i, share_i)                      # was: minimum_i + share_i
    if maximum_i is not None:
        sizes[i] = min(sizes[i], maximum_i)
```

- **`free` excludes flexible tracks' own minimums**, not only "whatever remains after
  they are subtracted": `free` is computed once, from the tree's fixed/intrinsic tracks
  only, so every flexible track's `share` is a stable proportion of the same pool
  regardless of how large any one track's minimum turns out to be. This is the single
  necessary change from the current code's `remaining = available - sum(sizes)`, which
  already includes each flexible track's minimum in `sizes` before `remaining` is
  computed — additive allocation is exactly "use `remaining` after minimums, then still
  add the minimum back underneath the share."
- A track whose `minmax` minimum is `0` (`fill`, plain `{fr: n}`) is numerically
  unaffected: `max(0, share) == 0 + share`. The prototype's isolation check (design plan,
  item 3) confirms this holds for every non-table flexible track in the public corpus —
  switching the rule cannot silently change a legend column, a plot `fill` track, or any
  other flexible track that does not also declare a nonzero `minmax` minimum today.
- This is the standards-aligned reading of `minmax`/`fr`: CSS Grid's own `fr` tracks use
  `max(base size, share)`, and Specification 33 §5 already names these keywords with the
  implication that they behave the way CSS Grid authors expect. Keeping the current
  additive rule would leave that vocabulary silently divergent from its own naming.
- **Migration is deliberate and disclosed**, not incidental: see the evidence's per-slide
  table. Under this rule, 17 of 18 affected public tables **shrink** below today's
  published width (26.7–151.4 px), because the corrected minimum usually already exceeds
  the small `fr` share those slots were given; one (`halcyon-1/replan-baseline`) grows
  6.0 px. This is accepted: the rule guarantees the minimum and nothing more, so a slot
  given a small `fr` share should not use the minimum-correction as a channel to also
  grow well past what its own share earns. An author who wants the table wider than its
  measured content raises its `fr` weight or its `max`, not its `min`.

## Why not keep additive allocation

Keeping the current additive rule together with the Contract 1 fix satisfies acceptance
criterion 1 alone, but it reproduces exactly the growth pattern the issue's own summary
names as the defect: "the flexible share adds on top of the minimum... widens the table
by roughly the whole difference," taking that space from the sibling track (usually the
timeline) on every corrected slide (+24.8 to +270.0 px in the evidence). Choosing additive
deliberately would still meet the letter of criterion 2 ("the meaning is specified"), but
it would specify the meaning the issue was filed to question, without any offsetting
benefit — the isolation check shows switching to `max(minimum, share)` does not cost any
additional public byte change beyond what raising the minimum already causes, since
exactly the same 18 slides move either way.

## Migration and compatibility

- No schema change. `minmax`, `min`, `max`, `fr` keep their existing spelling;
  Specification 33 §5's "remaining space" wording is amended to state the used-size
  formula precisely (below), not to add a keyword.
- No Theme, View, or metric-name change. `table.column.minInlineSize` is unchanged.
- **Specification 24 §2.1** gains one sentence: `minmax: {min: content}` on the table slot
  uses the same measured content extent as `preferred_inline`, so the slot's minimum is
  never smaller than its columns and gutters.
- **Specification 33 §5** gains the used-size formula for a flexible track:
  `max(minimum, share)`, with `share` computed from the space available to all flexible
  tracks before any of their own minimums are subtracted. This is a normative change to
  every `minmax`-with-nonzero-minimum flexible track in the engine, not only tables, so it
  is also recorded as [ADR-0032](../decisions/ADR-0032-flexible-track-minimum-is-a-floor.md).
- **Public evidence:** 18 of 21 materializers change (see the prototype evidence for the
  exact byte impact per slide). This is regenerated and attributed in one batch per
  implementation slice; representative before/after PNGs (HALCYON `01-mission-brief`,
  `orion-asic/gates`, and the two `print-mono` slides) are inspected, because several
  tables shrink and one sibling relation/plot-label suppression toggles per slide.

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
- `_allocate` with two flexible tracks, one given a `minmax` minimum larger than its
  share, resolves to exactly that minimum (not minimum-plus-share) while the sibling
  track absorbs the rest of `free`.
- `_allocate` with a zero-minimum `fill`/`{fr: n}` track produces the same size as before
  the change (regression guard for the isolation-check finding).
- `_allocate` with a `minmax` maximum still clips the flexible track under the new
  formula.
- A CLI render of one public layout under both the old and new rule, asserting the exact
  before/after widths recorded in the prototype evidence, as a golden regression guard for
  the deliberate migration.
