# Slice Review — Table `minmax` Content Minimum and Flex Allocation (#487)

**Commits:** `d1cfab4c` (design amendment, docs-only), `8f7ae47d` (implementation: code,
tests, regenerated evidence). **Design:** [design](../../design/issue-487-table-minmax-flex-allocation-design-2026-09-26.md),
as amended. **Authorities:** Specification 24 §2.1, Specification 33 §5,
[ADR-0032](../../decisions/ADR-0032-flexible-track-minimum-is-a-floor.md).
**CI:** pending.

Contracts 1 and 2 were implemented and published together, not as separate I487-1/I487-2
commits, per the implementation plan's own caution: I487-1 alone (raising the minimum
under additive allocation) produces an intermediate public state — every affected table
*grows* — materially different from, and strictly worse than, the final state where it
mostly *shrinks*. Publishing that intermediate state was explicitly discouraged in the
implementation plan, and both contracts landed together in commit `8f7ae47d`.

## What changed

- `layout/sources.py`'s `table` branch: `minimum_inline` is now the measured column and
  gutter extent (`_table_content_inline`) whenever the table has typed columns, instead
  of the widest row label. Unchanged when there are no typed columns.
- `layout/engine.py::_allocate`: the flexible-track resolution is now CSS Grid's
  iterative "find the size of an fr" algorithm (`_resolve_flexible_tracks`), not the old
  additive rule, and not the single-pass `max(minimum, share)` the architecture review
  first approved (corrected same-day, before this code was written — see the design
  amendment commit and ADR-0032).

## Re-measured public evidence (supersedes the design-phase prototype numbers)

The design-phase prototype (`docs/research/presentation/issue-487-table-minmax-flex-allocation-prototype-evidence-2026-09-26.md`)
measured the rejected single-pass formula. The table below is the actual, committed
result of the corrected iterative algorithm, measured by diffing `examples/*/generated/*`
before and after commit `8f7ae47d` (`tools/regenerate_public_examples.py --write` then
`--check`, 21/21 pass).

| Slide | Table width before → after (px) | Diagnostic attribution |
| --- | --- | --- |
| `aster-ssd/overview` | 542.4 → 458.4 (−84.0) | width only |
| `controller-z/annotations` | 542.4 → 458.4 (−84.0) | + `W_LAYOUT_NOTE_INDEX_SUPPRESSED:performance-note`; − `I_LAYOUT_PLOT_LABELS_SUPPRESSED:surface=table-timeline;count=1`, `W_LAYOUT_LABEL_SUPPRESSED:member-label:ga:ga` |
| `controller-z/composition-compact` | 549.6 → 465.6 (−84.0) | + `W_LAYOUT_RELATION_LABEL_SUPPRESSED:relation:bringup-to-performance:…`; − the same plot-label/member-label pair as `annotations` |
| `controller-z/elevated` | 542.4 → 458.4 (−84.0) | same as `composition-compact` |
| `controller-z/executive` | 542.4 → 458.4 (−84.0) | same as `composition-compact` |
| `controller-z/icons` | 542.4 → 458.4 (−84.0) | − the plot-label/member-label pair (no new diagnostic) |
| `controller-z/material-icons` | 542.4 → 458.4 (−84.0) | width only |
| `controller-z/plan-only` | 542.4 → 458.4 (−84.0) | width only |
| `controller-z-ja/executive` | 542.4 → 458.4 (−84.0) | width only |
| `halcyon-1/01-mission-brief` | 789.42 → 699.02 (−90.41) | width only |
| `halcyon-1/02-programme-board` | 410.50 → 383.83 (−26.67) | width only |
| `halcyon-1/03-launch-campaign` | 697.97 → 631.20 (−66.77) | width only |
| `halcyon-1/04-tvac-slip` | 389.50 → 326.99 (−62.50) | + `W_LAYOUT_RELATION_LABEL_SUPPRESSED:relation:tvac-emc:…`; − `W_LAYOUT_RELATION_LABEL_SUPPRESSED:relation:psr-shipment:…` |
| `halcyon-1/06-flight-readiness` | 921.19 → 823.64 (−97.55) | width only |
| `halcyon-1/07-replan-baseline` | 389.50 → 395.47 (**+5.97**) | width only |
| `halcyon-1/08-gallery-dark` | 789.42 → 699.02 (−90.41) | width only |
| `halcyon-1/09-gallery-mono` | 789.42 → 699.02 (−90.41) | width only |
| `orion-asic/gates` | 609.84 → 458.40 (−151.44) | width only |

18 of 21 materializers changed; `halcyon-1/overlay-briefing` (`inlineSize: content`, no
`minmax`) and 2 non-table slides are unaffected, exactly as the design predicted. Every
diagnostic addition/removal above was checked by diffing each slide's full `diagnostics`
list before and after (not only membership), so this table is exhaustive for the
18 changed slides — no diagnostic changed on a slide not listed with one.

**Attribution:** every width change is the direct, intended effect of Contract 1
(minimum raised to measured content) combined with Contract 2 (the corrected minimum
now typically exceeds the small `fr` share these table slots were given, so the
iterative algorithm freezes the table at its minimum rather than adding the old,
larger `additive` amount on top). `halcyon-1/replan-baseline` is the one slide whose
`fr` share exceeds its corrected minimum, so it grows slightly instead of shrinking.
Every diagnostic change is a direct, attributable consequence of the sibling
plot/relation surface gaining or losing room as the table's width changes — not an
independent regression. **No slide gained a `W_LAYOUT_VISIBLE_OVERFLOW` it did not
already have** (checked programmatically across all 21 slides).

**Correction from the design-phase prototype:** the rejected single-pass formula's
evidence reported `halcyon-1/replan-baseline` losing its `W_LAYOUT_AXIS_DENSITY` and
three `W_LAYOUT_AXIS_LABEL_THINNED` diagnostics, and several slides' relation-label
suppressions differed slightly (e.g. `controller-z/executive` showed only one new
relation-label suppression under the flawed formula's oversubscribed width, not the
corrected algorithm's non-oversubscribed width). The table above is the corrected,
authoritative record; the design-phase prototype evidence document is left unedited as a
historical record of what was measured during design, per `AGENTS.md`'s rule against
silently rewriting history.

## Visual inspection

Before/after PNG crops around the table were rendered for the three slides the lead
named (`resvg_py` + PIL):

- **HALCYON `01-mission-brief`** (−90.41 px): table text (all 16 rows, 5 columns) is
  unchanged and fully legible at the narrower width; the timeline gains visible room,
  showing group-header text (`Preliminary d…`, `Bus functional…`, `Critical desig…`)
  that was previously cropped out of this window.
- **`orion-asic/gates`** (−151.44 px, the largest shrink): table text (work package,
  revision, approval, Δ columns; group headers) is unchanged and fully legible; the
  freed width reveals Gantt bars, a milestone diamond, and axis labels in the timeline
  that were previously outside this crop window.
- **HALCYON `09-gallery-mono`** (−90.41 px, the `print-mono` slide that relies on this
  exact `minmax` slot as its #480 workaround): same pattern as `01-mission-brief` (same
  underlying view/layout, different color scheme) — table text intact, timeline gains
  room.

No garbling, overlap, or clipped table text was observed in any of the three. The
`print-mono` slide's workaround (giving the table slot `minmax: {min: content, max: {fr:
1}}` specifically because a plain `inlineSize: content` table had no slack for its own
last column, per `docs/research/presentation/preset-tuning/print-mono/README.md`) is
still served: the corrected minimum is still the table's true measured content, so the
slot still cannot be narrower than its own columns.

## Tests

- `tests/unit/chrona/presentation/layout/test_sources.py`: two #480-era assertions
  updated to the #487 contract (minimum equals measured content when columns are wider
  than the floor; minimum stays below the floor when columns are narrower; the
  zero-column fallback is now its own explicit test).
- `tests/unit/chrona/presentation/layout/test_flexible_track_allocation.py` (new): the
  min-exceeds-share redistribution (`Σ sizes == available`, the direct regression guard
  for the oversubscription bug the amendment fixes), the maximum-clamp redistribution
  (exercised directly, since the public grammar cannot express a flexible track with a
  finite maximum — see the design's Contract 2), the all-zero-minima regression guard
  (identical to the pre-#487 additive result), the minima-exceed-available overflow case,
  and one end-to-end `solve_layout` test through the public `minmax` grammar.
- `tests/integration/test_render.py`: `test_suppressed_plot_labels_have_one_completed_info_count`
  moved to the `mission-light` preset fixture (`inlineSize: content`, unaffected by
  #487) so it keeps testing the info-count/JSON-emission mechanism in isolation from this
  change; a new `test_controller_executive_draft_no_longer_suppresses_its_member_label_after_487`
  pins the attributed diagnostic change on the affected fixture and asserts no new
  `W_LAYOUT_VISIBLE_OVERFLOW`.
- Focused suite: `tests/unit/chrona/presentation`, `tests/integration`, `tests/cli` —
  771 passed, 1 skipped (pre-existing skip, unrelated).
- `conformance/run_conformance.py`: all 31 checks PASS. `diagnostic-inventory`,
  `presentation-contrast`, and `presentation-font-identity` were regenerated (stale only
  from the new table geometry and the `engine.py` line-number shift caused by extracting
  `_resolve_flexible_tracks`); `layout-float-accumulation` required whitelisting the new
  function for its Decimal-only `sum()` calls (same treatment as the existing `_allocate`
  entry it replaces).

## Literal acceptance (see the separate acceptance review for the formal table)

1. "`minmax: {min: content}` on a table slot is never narrower than its measured
   columns and gutters." — met: `minimum_inline` is now exactly that measure, and
   `_resolve_flexible_tracks` never resolves a track below its minimum (structural
   invariant of the algorithm; the explicit regression test covers the case that used to
   violate it).
2. "The flex-allocation meaning of a track minimum is specified (additive basis versus
   `max(min, share)`), and public evidence is migrated deliberately." — met: specified as
   CSS Grid's iterative resolution in Specification 33 §5 and ADR-0032 (not a bare
   `max(min, share)`, which the amendment shows is a different, incorrect meaning); the
   18-slide migration is measured, attributed per slide above, and visually inspected.

No open risk remains from the architecture review's flagged question (whether the lead
accepts tables becoming narrower than today): the lead approved with the algorithm
correction, which does not change that a majority of affected tables shrink — this was
confirmed, not revisited, by the correction.
