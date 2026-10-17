<!-- chrona:literal-acceptance/v1 -->

# Issue #1634 — opt-in forecast acceptance

Implementation reviewed: [PR #1646](https://github.com/tya5/chrona/pull/1646),
code611e8e8501bfa982202c674e272e906a8358eb52; subsequent changes are documents.
This review was a separate publication commit in the feature PR. Issue1634 is
closed after [release39019665585](https://github.com/tya5/chrona/actions/runs/39019665585)
passed on exact review-containing main `cf121865552017a2a97a13cd094bde641686c261`.

## Literal issue acceptance

### Issue #1634

- Source: [Issue #1634](https://github.com/tya5/chrona/issues/1634)
- Observed: 2026-10-17

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | Design and specification published before code: Spec 04 and 06 sections for the forecast layer, and the CLI/Context field. | met | [Design PR #1642](https://github.com/tya5/chrona/pull/1642); pre-code design a9c0d3ec6 and implementation plan 00d66e8a5. Observed-endpoint, occurrence and semantic-identity corrections ad9dcfb0d/cab0ae646/e0c26e3d4 preceded their corresponding implementation. | — |
| 2 | Synthetic tests: | met | [Focused scheduler tests](https://github.com/tya5/chrona/blob/611e8e8501bfa982202c674e272e906a8358eb52/tests/unit/chrona/usecases/test_forecast_schedule.py), with both literal sub-items below. | — |
| 3 | finished, started-late, started-overrunning and not-started items with a successor chain, on a working-day calendar; | met | [test_working_day_states_and_successor_chain](https://github.com/tya5/chrona/blob/611e8e8501bfa982202c674e272e906a8358eb52/tests/unit/chrona/usecases/test_forecast_schedule.py); source immutability and all four working-calendar states/chain asserted. | — |
| 4 | a `fixed-point` gate missed by a forecast successor is diagnosed. | met | [test_fixed_gate_miss_is_reported_without_moving_or_suppressing_it](https://github.com/tya5/chrona/blob/611e8e8501bfa982202c674e272e906a8358eb52/tests/unit/chrona/usecases/test_forecast_schedule.py); fixed coordinate retained, finding names gate/relation, absent analysis not borrowed. | — |
| 5 | Without `--forecast`, output is byte-identical to main. | met | [Exact-head official snapshot](https://github.com/tya5/chrona/actions/runs/39017645853), artifact12095378032 at611e8e850: all50 public SVG +50 Scene pairs byte-identical to base; every slide has0 routes/labels/primitives added,removed,changed. Only diagnostic/source-reference and declared-value inventory reports change. The exact public trial's target-b/technical-print SVG, Scene and PNG six-pair matrix also matches main ccf93c0e4 in separate venvs; later base changes are docs/report references only. | — |
| 6 | Trial 3's plan with its `actual.yaml` and `baseline.yaml`, rendered with `--forecast` in target-b and one generic preset: unfinished items carry an estimated Δ finish against the baseline, and no unfinished bar sits before as-of. Viewed as PNG. | met | Exact [public trial inputs](https://github.com/tya5/chrona/tree/dbbce45e60392b7b0be788f841fe2673f4830944/trial3), target-b and technical-print, 1600xauto, Actual + Snapshot + forecast. PNGs viewed on ccc4acf24 and repeated on611e8e850 with identical PNG bytes; technical-print Scene changes only the22 forecast plot-delta purposes, target-b Scene remains identical. Target-b: 25 forecast/ghost objects, 25 full deltas/22 estimates; technical-print: 22 selected objects, 22 independent deltas/19 estimates. Baseline ghosts and forecast legend visible. Started bars retain Actual start but extend to/after asOf; no unfinished bar lies wholly before it. | — |
| 7 | The skill's "Update the plan after a week of work" section mentions `--forecast`. | met | [Packaged skill](https://github.com/tya5/chrona/blob/611e8e8501bfa982202c674e272e906a8358eb52/skills/chrona/SKILL.md); 51 focused skill checks passed, existing 200-line limit retained. | — |

## Programme-level criteria (optional)

Require the feature PR's exact-head pytest shards, conformance and public
reproduction. Superseded runs with cancelled shards are not green evidence.
Focused integration groups: 83 forecast/routing, 244 CLI/MCP/closure and 158
Layout/Scene/geometry-guard tests passed; schema equivalence L1/L2/L3 passes.
Final semantic/vocabulary/forecast/Scene/label checks: 502 passed, 49 skipped.
Release39019665585 passed three-OS full pytest/conformance/wheel-smoke, newest-Python
public reproduction and MCP floor on the exact main SHA named above. Individual
required step outcomes were inspected before closure.

## Architecture conclusion

The application reuses its injected Scheduler on a non-persistent copy. Original
Project, Actual, progress and Snapshot remain source facts. Projection carries a
separate forecast comparison; Layout owns active geometry, full required deltas,
ghosts, ports, routes and legend. Scene/adapters only project/serialize completed
primitives. Per-occurrence channel coverage and shared chip/icon/text measurement
close folded/shared-row ownership. No copied preset, examples patch, second solver
or ordinary scheduler-success weakening. Forecast labels have distinct render identity with shared paint; the global uniqueness guard is unchanged. Independent audit found no ownership blocker.
