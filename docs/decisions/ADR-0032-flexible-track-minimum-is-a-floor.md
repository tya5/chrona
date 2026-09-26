# ADR-0032: A flexible track's `minmax` minimum is a floor, not an addend

- Status: Accepted
- Date: 2026-09-26
- Scope: Issue #487

## Context

Specification 33 §5 gives the Layout engine a CSS-Grid-shaped size vocabulary:
`minmax`, `{fr: n}`, `fill`. `layout/engine.py::_allocate` resolves a flexible track's
used size as `minimum + remaining × weight ÷ total_weight`: the declared minimum and the
proportional flex share are both added into the final size. CSS Grid's own `fr` tracks
instead resolve to `max(base size, share)` — the minimum is a floor the share must clear,
not an amount added underneath it.

This surfaced while fixing #480: `layout/sources.py`'s table source measure computed a
`minimum_inline` from the widest row label rather than the table's measured columns
(#487). Correcting that minimum exposed the allocator's additive behavior: raising a
`minmax: {min: content}` table's minimum to its true measured content widened the slot
by roughly the full amount of the correction, on 18 of 21 public materializers, taking
that space from a sibling flexible track (usually the timeline). A reverted prototype
(see the #487 evidence) showed this is not limited to the corrected minimum: any
nonzero `minmax` minimum on a flexible track already diverges between the two rules
today, whether or not that minimum is itself correct. In the public corpus, the only
flexible tracks with a nonzero minimum are these table slots — every `fill`/plain
`{fr: n}` track has `minimum == 0`, where the two rules coincide exactly
(`max(0, share) == 0 + share`).

## Decision

`_allocate`'s flexible-track used size becomes `max(minimum, share)`, where `share` is
computed from the space available to all flexible tracks before any of their own
minimums are subtracted (not from "whatever is left after minimums," which is what
made the old rule additive). A flexible track's `minmax` minimum is a guarantee — the
track is never smaller than it — not a base the flex share is layered on top of.

This is the standards-aligned reading of the vocabulary Specification 33 §5 already
names. It also does not change any flexible track in the current public corpus other
than the nine table layouts already in scope for #487: the isolation check in the
evidence confirms no zero-minimum flexible track's resolved size differs under the new
rule.

## Consequences

### Positive

- `minmax`'s minimum behaves the way its CSS-derived name implies, closing a silent gap
  between the schema's vocabulary and the engine's arithmetic.
- Raising a track's measured-content minimum (as #487 also does for the table source)
  no longer forces every sibling flexible track to give up space beyond what the
  correction actually requires; the table gets exactly its minimum unless its own `fr`
  share independently earns more.
- The change is provably scoped: only a flexible track that already declares a nonzero
  `minmax` minimum can produce a different number, and today that means exactly the
  table slots #480 and #487 already study.

### Costs

- 18 of 21 public materializers change bytes (table geometry, and several sibling-surface
  label/relation suppression toggles as a consequence of the table's new width). Every
  change must be attributed per slide in the implementation slice review, not merely
  regenerated.
- 17 of those 18 tables become **narrower** than their currently published width (26.7–
  151.4 px), not merely "less wide than an over-corrected fix" — this is a visible,
  deliberate output change an issue owner or reviewer must accept, not an incidental
  side effect.
- Any future flexible track that combines a nonzero `minmax` minimum with a small `fr`
  share will, from this point on, size to its minimum rather than to minimum-plus-share;
  authors relying on the old additive behavior to pad a track past its stated minimum
  must instead raise that track's own minimum, `fr` weight, or `max`.

## Rejected alternatives

1. **Keep additive allocation.** Satisfies the issue's literal wording ("the meaning is
   specified") without addressing why it was raised: it reproduces the exact
   uncontrolled-growth pattern the issue's summary calls out, and offers no corpus-impact
   benefit over switching rules (the same 18 slides change either way).
2. **Scope the new rule to table slots only (e.g. a table-specific allocator).** Rejected:
   the engine has one `_allocate` function for every node kind and axis by design
   (Specification 33 §8); a source-specific carve-out would duplicate the flex-resolution
   algorithm for no corpus benefit, since the isolation check shows the general rule
   already only affects the table slots in practice.
3. **A new size keyword (e.g. `minmax-strict`) that opts into `max(min, share)` while
   leaving existing `minmax` additive.** Rejected: it doubles the vocabulary for a
   behavior CSS Grid's own `minmax` already implies, and every public profile would need
   a syntax migration instead of a semantics one, for the same corpus-wide byte impact.
