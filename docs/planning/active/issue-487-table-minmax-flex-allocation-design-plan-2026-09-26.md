# Design Plan — Table `minmax` Content Minimum and Flex Allocation (#487)

**Public base:** `bf98f9b0` on `main`. **Source of truth:** [Issue #487](https://github.com/tya5/chrona/issues/487), Specifications 24 §2.1 and 33 §5, and the [#480 design](../../design/issue-480-table-and-row-metrics-design-2026-09-26.md) it was filed from. **Related:** #480 (closed; fixed `inlineSize: content` only and filed this issue), #433 (coverage honesty).

## Published baseline, inference, and unverified facts

Reproduced on `bf98f9b0` (the current public base) by reading the code and by measuring an
unpublished, throwaway prototype (reverted; not committed) against all 21 public
materializers.

1. **`min: content` is not the table's content.** `layout/sources.py::measure_sources`'s
   `table` branch (around line 169) sets:
   ```
   minimum_inline = min(column_floor, text_inline)
   preferred_inline = max(column_floor, measured_content)   # via _table_content_inline, #480
   ```
   `text_inline` is the widest row label text, not the table's measured columns.
   `preferred_inline` already uses the real measured content extent (`_table_content_inline`,
   added by #480), but `minimum_inline` never sees it. A slot at
   `inlineSize: {minmax: {min: content, max: {fr: N}}}` therefore has a declared minimum
   that can be smaller than its columns. Nine public layouts (`bundles/print-mono`,
   `bundles/executive-light`, `bundles/elevated-light`, and the `examples/*/layouts/*`
   files that use the same pattern) use exactly this spec on the table slot.
2. **A flexible track's minimum is additive, not a CSS-grid `max(min, share)`.**
   `layout/engine.py::_allocate` computes, for every flexible (`fr`/`fill`) track:
   ```
   sizes[i] = minimum_i             # initial
   remaining = available - sum(sizes)
   sizes[i] += remaining * weight_i / total_weight   # added ON TOP of minimum_i
   ```
   CSS Grid's `minmax(min, max)` semantics for an `fr` track instead give
   `max(min, share)`: the minimum is a floor the share must clear, not an amount the
   share is added to.
3. **Verified impact (prototype, reverted).** I measured three configurations against
   all 21 public materializers using `tools/materialize_example.py`'s `write=False` path
   (a throwaway script, not committed):
   - **Baseline** (current `main`): 0 of 21 mismatch, as expected.
   - **Candidate A** — raise `minimum_inline` to the measured content extent, keep the
     current additive `_allocate`: 18 of 21 materializers mismatch (the 19th table slide,
     `halcyon-1/overlay-briefing`, uses `inlineSize: content` with no `minmax`, so its
     size is unaffected; the other 2 of 21 have no table source). Every changed table
     **grows** by 25–270 px (HALCYON `01-mission-brief`: 789.4 → 1059.5 px, matching the
     number already cited in the #480 evidence), taking that space from the sibling
     `fr` track (usually the timeline).
   - **Candidate B** — same minimum-inline fix, plus `_allocate` changed to
     `max(minimum, share)`: the **same** 18 of 21 materializers mismatch. Most tables
     **shrink** relative to the current baseline (25–151 px smaller, e.g. `orion-asic/gates`
     609.8 → 458.4 px), because the corrected minimum is usually larger than the track's
     fr share, so it dominates instead of adding to it. One slide (`halcyon-1/replan-baseline`)
     grows slightly (+6.0 px) because its share exceeds its minimum.
   - **Isolation check** — `_allocate` changed to `max(minimum, share)` **without** raising
     `minimum_inline` (old, too-small minimum kept): still the same 18 of 21 mismatch. This
     shows the allocation-semantics choice is *not* coupled to the minimum-inline fix: any
     nonzero `minmax` minimum already produces a different number under the two rules. In
     the public corpus, the only nonzero-minimum flexible tracks are these nine table
     layouts (`fill`/plain `{fr:n}` tracks have `minimum == 0`, where `max(0, share) == 0 +
     share`, so the two rules coincide and every non-table flexible track is untouched by
     the semantics choice).
   - Both candidates change roughly the same warning classes: relation-label suppression,
     plot-label suppression, and note-index suppression toggle on 6–7 of the 18 changed
     slides, in different combinations per candidate. Neither candidate is warning-free.
4. **`print-mono` depends on this exact slot spec.** `docs/research/presentation/preset-tuning/print-mono/README.md`
   records that the preset gives the table slot `minmax: {min: content, max: {fr: 1}}`
   specifically to work around the #480 content-sizing gap (a plain `inlineSize: content`
   table had no slack for its own last column). Both `halcyon-1/gallery-mono` and
   `halcyon-1/launch-campaign` are in the 18-slide changed set above.
5. Unverified until the design decision: whether the owner accepts that a technically
   correct fix can make several published tables **narrower** than today, not only "less
   wide than an over-eager fix" — see the open decision below.

## Literal issue acceptance ledger

1. "`minmax: {min: content}` on a table slot is never narrower than its measured columns
   and gutters."
2. "The flex-allocation meaning of a track minimum is specified (additive basis versus
   `max(min, share)`), and public evidence is migrated deliberately."

## Use cases and decisions to close

1. **Table minimum measure.** An author who writes `minmax: {min: content, max: {fr: N}}`
   on the table slot gets a slot that is never narrower than the table's measured columns
   and gutters, using the same `_table_content_inline` measure #480 already computes for
   `preferred_inline`. Decide: does `minimum_inline` become exactly the measured content
   extent, or `min(column_floor, measured content)`-style flooring analogous to
   `preferred_inline`'s `max(column_floor, measured)`? (Since `preferred_inline` already
   is `≥` the measured content by construction, setting `minimum_inline` to the measured
   content directly cannot exceed `preferred_inline`; no additional flooring is needed.)
2. **Flex allocation semantics for a `minmax` minimum.** Decide between:
   - **keep additive** (`minimum + share`): satisfies criterion 1 alone, but reproduces
     exactly the uncontrolled growth the issue's summary complains about, taking room
     from a sibling track for every corrected slide;
   - **switch to `max(minimum, share)`** (CSS Grid's own `fr`/`minmax` mental model,
     which this schema's vocabulary already borrows): satisfies criterion 1, bounds the
     table to no more than it needs unless its own `fr` share is larger, and — per the
     isolation check above — provably does not change the numeric result of any other
     flexible track in the public corpus;
   - a third option (e.g. a new size keyword, or scoping the semantics change to table
     slots only) is not identified as necessary: the isolation check shows the semantics
     change is already scoped to nonzero-minimum tracks by construction, and the schema
     has one `_allocate` function, not a per-source one.
   The design plan's recommendation, pending architecture review, is `max(minimum,
   share)`, because it is the standards-aligned reading of `minmax`/`fr` this schema
   already names, and it does not touch any flexible track whose minimum is zero.
3. **Deliberate migration disclosure.** Whichever rule is chosen, several public tables
   change size (grow under additive, mostly shrink under `max(min, share)`), and several
   suppression warnings toggle. Both must be attributed slide-by-slide in the slice
   review/batch diff, and representative before/after PNGs inspected, per `AGENTS.md`.

## Responsibility and architecture review questions

- Layout owns measurement and allocation (Specification 33 §§5, 8; the #403/#404 and
  #480 corrections). Both fixes stay inside `layout/sources.py` (`measure_sources`) and
  `layout/engine.py` (`_allocate`/`_spec_base`); no other layer changes.
- Does the `max(minimum, share)` rule change Specification 33 §5's wording for `fr`
  ("a proportion of remaining space")? Yes — "remaining space" must be defined precisely
  (space after removing fixed/intrinsic tracks, *not* after removing flexible tracks'
  own minimums), and the used-size formula for a flexible track must be stated. This is
  a normative amendment, not merely a design note, because it changes engine behavior for
  every existing and future `minmax`-with-nonzero-minimum profile, not only tables. It is
  the kind of decision `AGENTS.md` requires an ADR for (a public schema/engine semantics
  change with a migration impact), in addition to the Specification 24/33 text.
- Does this interact with #467's row-height work or #466's placement model? No: both are
  block-axis/row-requirement concerns; this issue is inline-axis flex distribution and the
  table's own `min_inline`. No shared function changes.
- Does `table.column.minInlineSize`'s meaning change? No: it stays the per-column floor
  for `preferred_inline` that #480 already stated; this issue only changes `minimum_inline`.

## Ordered design slices and acceptance evidence

1. **D487-1: prototype evidence.** Already collected above (design-plan-embedded); publish
   the fuller table as `docs/research/presentation/issue-487-table-minmax-flex-allocation-prototype-evidence-2026-09-26.md`.
2. **D487-2: contract.** Choose the minimum-inline rule and the flex-allocation semantics.
   Amend Specification 24 §2.1 (minimum-inline rule) and Specification 33 §5 (flex
   semantics), and add an ADR for the engine-wide semantics change. Publish
   `docs/design/issue-487-table-minmax-flex-allocation-design-2026-09-26.md`.
3. **D487-3: whole-architecture review.** Check the contract against Layout ownership,
   the #480 boundary, the print-mono workaround, and the full 21-materializer batch.
   Publish under `docs/reviews/current/`.
4. **D487-4: implementation plan.** One slice for `sources.py` (minimum-inline), one for
   `engine.py` (`_allocate`), evidence regeneration, and focused tests for both axes plus
   the interaction between them.

Issue acceptance needs a separate review with one row per literal criterion, direct test
and rendered-output evidence, the batch materializer diff, and the green CI matrix.
