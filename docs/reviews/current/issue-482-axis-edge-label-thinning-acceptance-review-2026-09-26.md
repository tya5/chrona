<!-- chrona:literal-acceptance/v1 -->

# Release Review — Axis Edge Label Thinning (#482)

**Reviewed product:** `8a08a9e2` on `main`. **Design:** [design](../../design/issue-482-axis-edge-label-thinning-design-2026-09-26.md), [architecture review](issue-482-axis-edge-label-thinning-architecture-review-2026-09-26.md), Specification 39 §1.1. **Slice review:** [I482-1/I482-2](issue-482-axis-edge-label-thinning-i482-1-review-2026-09-26.md).

## Literal issue acceptance

### Issue #482

- Source: [Issue #482](https://github.com/tya5/chrona/issues/482)
- Observed: 2026-09-26

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | `thin-with-record` removes only labels that collide. A test with one colliding edge label keeps all the others. | met | [Slice review](issue-482-axis-edge-label-thinning-i482-1-review-2026-09-26.md): `test_thinning_schedule_keeps_every_fitting_label_for_one_colliding_edge_label`, `test_thin_with_record_drops_only_one_disproportionately_wide_label`, `test_orion_gates_measures_the_colour_scale_legend_before_layout`, `test_replan_baseline_records_the_nonfitting_partial_quarter_label`. All four fail against `42f36769` and pass against `8a08a9e2`. | — |
| 2 | A partial edge cell narrower than its label does not collide with its neighbour. | met | [Slice review](issue-482-axis-edge-label-thinning-i482-1-review-2026-09-26.md): `test_replan_baseline_records_the_nonfitting_partial_quarter_label`'s pairwise no-intersection assertion over every placed axis label; before/after CLI reproduction of the marginDays sliver-month case (English and ja-JP) shows the clipped candidate thinned, not drawn overlapping its neighbour. | — |
| 3 | `marginDays` can be used by the presets without an axis warning. | met | [Slice review](issue-482-axis-edge-label-thinning-i482-1-review-2026-09-26.md): `test_cli_margin_days_produces_no_axis_warning_on_every_catalogue_preset`, all five catalogue presets, HALCYON-1 and a `chrona init` starter: no `W_LAYOUT_LABEL_OVERFLOW` or `W_SCENE_TEXT_INTERSECTION` naming an axis label. | — |

## Programme-level criteria (optional)

- The reproduction from the issue is closed end to end through the CLI:
  - `mission-light` + `window: {mode: selected-planned, marginDays: 7}` + month labels `thin-with-record` on HALCYON-1: before, 5 of 10 month labels placed (every second dropped); after, 9 of 10 placed, only the genuinely clipped one thinned.
  - The ja-JP quarter comment (`--locale ja-JP`, `mission-light` preset, `07-replan-baseline` View): before, only `2027年Q3` placed (`2027年Q4` dropped alongside the clipped `2027年Q2`); after, both `2027年Q3` and `2027年Q4` placed.
- Public evidence changed only as attributed in the [slice review](issue-482-axis-edge-label-thinning-i482-1-review-2026-09-26.md): `examples/orion-asic/generated/gates.{svg,scene.json}` and `examples/halcyon-1/generated/07-replan-baseline.{svg,scene.json}` each show their previously-dropped, actually-fitting axis labels, with identical geometry for every label already placed. `docs/diagnostics/inventory.md` (line numbers only) and `docs/diagnostics/presentation-font-identity.md` (placement counts) were refreshed; `docs/diagnostics/presentation-contrast.md` was unaffected.
- `conformance/run_conformance.py`: PASS, all 31 checks.
- Focused tests: `tests/unit/chrona/presentation tests/integration tests/cli` — 772 passed, 1 skipped (pre-existing).
- CI: [four-job CI run 36248123399](https://github.com/tya5/chrona/actions/runs/36248123399) on `908f9d69`, green: Ubuntu, Windows and macOS conformance/full pytest/wheel, and newest-Python public materializer reproduction. The implementation landed as `1dee7f1e` (cherry-picked; the axis-label count constant became 180 after integrating the new #430 slide).

## Architecture conclusion

`thin-with-record` remains a deterministic Layout policy over completed interval outcomes (unchanged layer ownership from the accepted [axis thinning record amendment](../../design/issues-405-406-407-408-400-axis-thinning-record-design-amendment-2026-09-25.md)). The correction replaces a whole-tier periodic stride/phase search with a direct per-candidate filter, since one candidate's measured fit against its own clipped, contiguous interval never depends on any other candidate's disposition. `AxisThinningSchedule`'s `stride`/`phase` fields and the `"thinning-stride"` outcome reason are retired as dead concepts; `surface_quality.py`'s `AxisTierOutcome` invariant was tightened in the same commit. Specification 39 gained §1.1 stating the corrected rule normatively. No View, Theme, Scene, adapter or schema change; #426 (axis tier appearance) is untouched, as named in the design and confirmed by the diff touching only `thinning_schedule`'s selection rule and its two call sites.

Release disposition: all three literal rows are met.
