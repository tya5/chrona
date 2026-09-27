# Implementation Plan — Table `minmax` Content Minimum and Flex Allocation (#487)

**Public design base:** the commit that publishes the [architecture review](../../reviews/current/issue-487-table-minmax-flex-allocation-architecture-review-2026-09-26.md).
**Authority:** [design](../../design/issue-487-table-minmax-flex-allocation-design-2026-09-26.md),
Specification 24 §2.1, Specification 33 §5, [ADR-0032](../../decisions/ADR-0032-flexible-track-minimum-is-a-floor.md),
[Issue #487](https://github.com/tya5/chrona/issues/487).

**Awaiting confirmation:** the architecture review's open question (does the lead/owner
accept that most affected tables become narrower than today's published width, not only
less wide than an additive fix). Do not start I487-2 until this is confirmed; I487-1 is
independent of it.

## Literal acceptance ledger

1. "`minmax: {min: content}` on a table slot is never narrower than its measured columns
   and gutters."
2. "The flex-allocation meaning of a track minimum is specified (additive basis versus
   `max(min, share)`), and public evidence is migrated deliberately."

## Coordination

No other open issue owns `layout/sources.py`'s `table` branch or `layout/engine.py::_allocate`.
#467/#466 (other dev session) do not touch either file. Before each push, fetch
`origin/main`, check ahead/behind, and stop on a conflict in `layout/sources.py` or
`layout/engine.py`.

## I487-1: table `min_inline` is the measured content

**Owners/files:**
- `layout/sources.py`: the `table` branch of `measure_sources` — `minimum_inline` becomes
  `_table_content_inline(...)`'s result when `value.table.columns` is non-empty; the
  existing `min(column_floor, text_inline)` fallback is kept for the zero-column case.

**Focused tests:**
- a `minmax: {min: content, max: {fr: 1}}` table slot's resolved `minimum_inline` equals
  `_table_content_inline` for a multi-column, hierarchy-bearing fixture;
- a zero-column table source keeps today's fallback (regression guard);
- `minimum_inline ≤ preferred_inline` holds for every fixture (a structural invariant,
  not only a numeric coincidence).

**Public evidence:** this slice alone (additive allocation still in place) changes the 18
slides by the "Candidate A" amounts in the evidence — every affected table grows. This is
an intermediate state; do not publish it alone if I487-2 is expected within the same
release, since it produces a public state materially different from the final one (grows
instead of shrinks). If I487-1 must ship independently, say so in its slice review and
link forward to I487-2.

**Gate:** focused tests (`tests/unit/chrona/presentation`, `tests/integration`,
`tests/cli`), conformance, 21-materializer batch (attributed), then push and the four-job
CI.

## I487-2: `max(minimum, share)` flexible-track allocation

**Owners/files:**
- `layout/engine.py::_allocate`: replace the additive step with the `max(minimum, share)`
  resolution described in the design, computing `free` from non-flexible track sizes
  only, before any flexible track's own minimum is considered.

**Focused tests:**
- two flexible tracks, one with a `minmax` minimum larger than its share: resolves to
  exactly that minimum, and the sibling absorbs the rest of `free` (not the other way
  around);
- a zero-minimum `fill`/`{fr: n}` track: identical resolved size before and after the
  change (regression guard for the isolation-check finding — this is the test that
  proves the change does not leak beyond nonzero-minimum tracks);
- a `minmax` maximum still clips the resolved size after the `max(minimum, share)` step;
- a CLI render of HALCYON `01-mission-brief` (or an equivalent fixture) asserting the
  exact table width from the evidence, as a golden regression guard for the deliberate
  migration.

**Public evidence:** the full 18-slide change from the evidence's "Candidate A+B" column.
Attribute every changed Scene/SVG byte to either the table-width change or a downstream
suppression toggle (relation label, plot label, note index, axis thinning — see the
evidence's diagnostics table for the expected set per slide). Render before/after PNG
crops for HALCYON `01-mission-brief`, `orion-asic/gates` (largest shrink, −151.4 px), and
both `print-mono` slides (`halcyon-1/gallery-mono`, `halcyon-1/launch-campaign`), and look
at them — this slice is expected to visibly tighten several tables, and the review must
confirm that is acceptable, not merely that the diff matches the evidence.

**Gate:** as I487-1. Additionally run `.venv/bin/python conformance/run_conformance.py`
and refresh `diagnostic-inventory`/`presentation-contrast` if stale, since the diagnostic
churn is expected and by design here.

## I487-3: issue acceptance

A separate acceptance review under `docs/reviews/current/`, with one row per literal
criterion, the two focused-test links, CLI output for the `minimum_inline` fixture and
the `_allocate` fixtures, the 21-materializer batch diff (attributed per slide), the
before/after PNGs, and the green CI run. Close #487 only then.

If a slice exposes a public slide whose new width triggers a diagnostic not already
anticipated in the evidence, or a conflict with #466/#467's row/placement paths, pause,
publish a design correction, and amend this plan.
