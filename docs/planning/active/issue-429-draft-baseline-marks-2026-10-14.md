# Issue #429: draft baseline marks for the packaged designs (work record)

Living record for slice P429-4 of [#429](https://github.com/tya5/chrona/issues/429). Edited in place.

**Public base:** `ac4ac8836` on `main`.

## Baseline

- The five approved designs in `src/chrona/resources/designs/` each declare `viewDefaults.comparison.baselineMarks: ghost-when-changed`.
- `chrona render` (draft) has no Snapshot Project, so projection raises `E_REVIEW_BASELINE_MARKS_SNAPSHOT` for every View that inherits the default. No design can render as a named preset.
- The View schema offers only `ghost` and `ghost-when-changed`; a View cannot switch the inherited mark off.

## Rule

`comparison.baselineMarks: ghost-when-changed` draws a ghost only for an item whose Snapshot placement differs from its current one.

| Case | Before | After |
| --- | --- | --- |
| `ghost-when-changed`, snapshot baseline and Snapshot present | ghosts where the baseline moved | unchanged (byte-identical) |
| `ghost-when-changed`, no snapshot baseline or no Snapshot | `E_REVIEW_BASELINE_MARKS_SNAPSHOT` | no ghost, no diagnostic |
| `ghost`, no snapshot baseline or no Snapshot | `E_REVIEW_BASELINE_MARKS_SNAPSHOT` | unchanged (still the error) |
| explicit rows | unchanged | unchanged |

Rationale: `ghost-when-changed` is conditional by name ("when changed"); with no baseline nothing has changed. `ghost` promises a ghost for every item and so still requires a baseline.

## Files and tests

- `src/chrona/presentation/model/projection.py` (the one check), `docs/specification/06-view-model.md` (Comparison paragraph), `schemas/view-v0.28.schema.yaml` (description only).
- `tests/unit/chrona/presentation/model/test_projection_rows.py`: draft case (no baseline, and snapshot baseline with no Snapshot) draws no ghost; `ghost` still errors; the existing snapshot case is unchanged.
