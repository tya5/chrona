# Implementation Plan — Axis Edge Label Thinning (#482)

**Public design base:** the commit that publishes the [architecture review](../../reviews/current/issue-482-axis-edge-label-thinning-architecture-review-2026-09-26.md). **Authority:** [design](../../design/issue-482-axis-edge-label-thinning-design-2026-09-26.md), Specification 39 §1.1, [Issue #482](https://github.com/tya5/chrona/issues/482).

## Literal acceptance ledger

1. "`thin-with-record` removes only labels that collide. A test with one colliding edge label keeps all the others."
2. "A partial edge cell narrower than its label does not collide with its neighbour."
3. "`marginDays` can be used by the presets without an axis warning."

## Coordination

No other open issue owns these files. #426, #466, #467, #478 are named-not-touched per the architecture review; if a slice's diff would touch `AxisTierOutcome.role`, any file under the other session's #466/#467 ownership, or axis tier appearance, pause and re-check the review before continuing.

## I482-1: per-candidate thinning rule

**Owners/files:**
- `src/chrona/presentation/layout/axis.py`: replace `thinning_schedule`'s stride/phase search with the direct filter; change `AxisThinningSchedule` to `(retained_positions, thinned_positions)`.
- `src/chrona/presentation/layout/surface_composer.py`: the `thin-with-record` block (`schedule.retained_positions`, the per-candidate `reason` assignment — now always `"label-does-not-fit"` for a thinned candidate — and the `W_LAYOUT_AXIS_DENSITY` diagnostic payload, `stride=`/`phase=` → `thinned=<count>`).
- `src/chrona/presentation/layout/surface_quality.py`: `AxisTierOutcome.__post_init__`, drop `"thinning-stride"` from the allowed `reason` set for a `thinned` disposition.

**Focused tests (`tests/unit/chrona/presentation/layout/test_axis_placement.py`):**
- `thinning_schedule((False, True, False, True))` → `retained_positions=(1, 3)`, `thinned_positions=(0, 2)`.
- `thinning_schedule` with one failing position among nine fitting ones → `retained_positions` is all eight fitting positions; only the one failing position is thinned (this is the literal "one colliding edge label keeps all the others" test).
- `thinning_schedule` with all-`False` input still raises `ValueError("E_PRESENTATION_AXIS_OVERFLOW")` (unchanged fallback invariant).
- `surface_quality.py`: an `AxisIntervalOutcome` with `disposition="thinned", reason="thinning-stride"` now fails `AxisTierOutcome.__post_init__`'s invariant (was previously accepted).

**Gate:** run before touching `surface_composer.py`'s call site, since the corrected `axis.py` function and test change first, in isolation.

## I482-2: composer call site and collision-free rendering

**Owners/files:** `surface_composer.py` (the composer changes started in I482-1 land fully here, since they are one coherent change to one code path — kept as a separate slice only for review granularity, not a separate commit if the diff is small enough to review as one unit; if split, this slice is the composer + `surface_quality.py` half).

**Focused tests (CLI-level, `tests/cli` or `tests/integration`):**
- `chrona render` on a copied `mission-light` preset with `window: {mode: selected-planned, marginDays: 7}` and month-label `overflow: thin-with-record` against `examples/halcyon-1`: the scene carries exactly one `W_LAYOUT_AXIS_LABEL_THINNED:...:label-does-not-fit` and no `thinning-stride` reason; `Apr, Jun, Aug, Oct` (or the current build's equivalent interior months) are placed.
- The same fixture rendered with month-label `overflow: visible-overflow` instead (to isolate that the fix is in thinning, not in `axis_label_fits`) still shows the pre-existing `W_SCENE_TEXT_INTERSECTION`; the acceptance path is `thin-with-record` removing it, not a change to fit measurement.
- A dedicated test asserting no two placed `axisLabel` primitives' bounds intersect, for the `marginDays` + `thin-with-record` fixture (covers acceptance item 2 directly at the geometry level, following the pattern already used by `test_replan_baseline_records_the_nonfitting_partial_quarter_label`).
- `marginDays` used on the `mission-light`-shaped configuration produces no diagnostic beyond the one genuine `label-does-not-fit` (covers acceptance item 3 as the natural consequence of item 1, per the design).

**Public evidence:** update the two fixtures the design names as already affected:
- `examples/orion-asic` (`gates` context) and `examples/halcyon-1` (`07-replan-baseline` context): re-run `tools.materialize_example`/`tools.regenerate_public_examples --write` then `--check`; `test_materialize_example.py`'s `test_orion_gates_measures_the_colour_scale_legend_before_layout` and `test_replan_baseline_records_the_nonfitting_partial_quarter_label` are updated to the corrected diagnostics (no `stride=`/`phase=`, `thinned=<count>` instead) and gain an assertion that the previously-dropped fitting labels are now present.
- Full 21-materializer batch (`tools.regenerate_public_examples --write --jobs 6` then `--check`) to confirm no other fixture changes; if one does, attribute it (it means another public fixture also has a clipped edge bucket under `thin-with-record`, which is in scope for this fix, not a defect) before accepting the slice.
- Before/after PNG crop of `orion-asic` `gates` and `halcyon-1` `07-replan-baseline`'s axis, inspected directly (resvg_py + PIL).

**Gate:** focused tests (`tests/unit/chrona/presentation`, `tests/integration`, `tests/cli`), `conformance/run_conformance.py`, the 21-materializer batch, then push and the CI matrix. The slice review is published separately.

## Open decision carried from the architecture review

The ja-JP quarter comment's exact CJK case (`--locale ja-JP` with a `Noto Sans JP` font descriptor) was reproduced only mechanistically (via the English `07-replan-baseline` quarter case), not as a locale-specific fixture, because none of the public examples currently pair a ja-JP render context with a clipped quarter edge. Decide, before I482-3, whether to add one (for example a ja-JP variant context or CLI-level test using `packages/chrona-fonts-noto-cjk`) as direct regression coverage for the comment, or to rely on the locale-independence already enforced by `test_axis_label_path_has_no_language_code_branch` plus the English fixture. Either is consistent with the design; this only needs the owner's preference before closing I482-3.

## I482-3: issue acceptance

Separate acceptance review under `docs/reviews/current/`, with a row per literal criterion, test links, the two reproduction CLI outputs (thin-with-record and visible-overflow) from the design/evidence documents, the attributed materializer diff, and the green CI run. Close #482 only then.

If a slice exposes a public fixture whose changed bytes are not explained by "more fitting labels placed, same geometry," or a conflict with #426/#466/#467's files, pause, publish a design correction, and amend this plan.
