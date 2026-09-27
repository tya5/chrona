# Reproduction Evidence — Axis Edge Label Thinning (#482)

This is evidence for the [#482 design plan](../../planning/active/issue-482-axis-edge-label-thinning-design-plan-2026-09-26.md), collected on public base `bf98f9b0` with `chrona preset copy mission-light --output work/ml`, `window: {mode: selected-planned, marginDays: 7}`, month labels `overflow: thin-with-record`, and `chrona render examples/halcyon-1/project.yaml --actual examples/halcyon-1/actual.yaml --preset work/ml/preset.yaml --emit-scene`. No product code was changed to collect this evidence.

## Scale and clipped edge bucket

```
scale: domainStart=2027-02-26 domainEnd=2027-11-26 rangeStart=522.0 rangeEnd=1564.0 unitRatio=3.8168
```

`marginDays: 7` moves the window start from the earliest planned date (2027‑03‑05) back to 2027‑02‑26, seven days before it, clipping the first month bucket to 3 days.

## Measured month grid boundaries (`axis-grid:4:*`, tier index 4)

| index | x | width (px) |
| --- | --- | --- |
| 0 (Feb, clipped) | 522.00 | **11.45** |
| 1 (Mar) | 533.45 | 118.32 |
| 2 (Apr) | 651.77 | 114.51 |
| 3 (May) | 766.28 | 118.32 |
| 4 (Jun) | 884.60 | 114.51 |
| 5 (Jul) | 999.11 | 118.32 |
| 6 (Aug) | 1117.43 | 118.32 |
| 7 (Sep) | 1235.75 | 114.51 |
| 8 (Oct) | 1350.26 | 118.32 |

`"Feb"` measures wider than 11.45 px; every other candidate's own three-letter label (measured 16.6–27.5 px, from the placed primitives below) fits its own 114–118 px cell with wide margin.

## Diagnostics with `thin-with-record` (buggy today)

```
W_LAYOUT_AXIS_LABEL_THINNED:axis-label:3:0:label-does-not-fit
W_LAYOUT_AXIS_LABEL_THINNED:axis-label:3:2:thinning-stride
W_LAYOUT_AXIS_LABEL_THINNED:axis-label:3:4:thinning-stride
W_LAYOUT_AXIS_LABEL_THINNED:axis-label:3:6:thinning-stride
W_LAYOUT_AXIS_LABEL_THINNED:axis-label:3:8:thinning-stride
W_LAYOUT_AXIS_DENSITY:axis-tier:3:stride=2:phase=1
```

Placed primitives: only `Mar` (25.9 px), `May` (27.5 px), `Jul` (16.6 px), `Sep` (23.1 px), `Nov` (26.1 px). `Apr`, `Jun`, `Aug`, `Oct` are dropped although each has 90+ px of unused room — the issue's literal report ("removed every second month label ... although those had ample room").

`thinning_schedule((False, True, True, True, True, True, True, True, True, True))` returns `stride=2, phase=1`, because `stride=1` fails on position 0 and no arithmetic progression can express "everything except position 0".

## Diagnostics with the tier's current default (`visible-overflow`) instead of `thin-with-record`

Same window, same clipped February bucket, month label `overflow: visible-overflow` (`mission-light`'s unmodified declaration):

```
{"code": "W_LAYOUT_LABEL_OVERFLOW", "failureKind": "label-collision", "placementId": "axis-label:3:0", ...}
{"code": "W_SCENE_TEXT_INTERSECTION", "findingCode": "E_SCENE_TEXT_INTERSECTION",
 "primitiveIds": ["axis-label:3:0", "axis-label:3:1"], "measuredFacts": {"area": 212.27, "threshold": 4.0}}
```

This is a genuine, geometry-checked overlap (`W_SCENE_TEXT_INTERSECTION`) between the clipped February label and the March label that follows it — the issue's second report, reproduced directly. It confirms that `axis_label_fits`'s self-containment check (label width vs. the candidate's own clipped interval width) is a sufficient predicate for "this label would collide with its neighbour": axis buckets from `axis_intervals` are contiguous and half-open, so a label that stays inside its own bucket cannot reach a neighbour's bucket. Suppressing exactly the non-fitting candidate (as `thin-with-record` already does for position 0 above) removes the intersection with no further geometry work.

## Existing public evidence already carrying this defect

Unmodified `bf98f9b0` already exercises the identical mechanism (a clipped edge bucket under `thin-with-record`) in two published example fixtures, asserted by `tests/integration/test_materialize_example.py`:

- `examples/orion-asic` (`gates` context): `axis-tier:3`, `axis-label:3:0` clipped, resulting `stride=2:phase=1`.
- `examples/halcyon-1` (`07-replan-baseline` context, an **explicit** `window.start` of `2027-06-28` that clips the first quarter and month, not `marginDays`): `axis-tier:2` (quarter) and `axis-tier:3` (month) both show the same `label-does-not-fit` + `stride=2:phase=1` pattern.

Both fixtures currently pass a same-file assertion that no two placed axis labels' rendered bounds intersect (`test_replan_baseline_records_the_nonfitting_partial_quarter_label`). That property must still hold after the fix — it holds today only because over-thinning happens to remove more than the minimum; the corrected rule keeps it by removing exactly the non-fitting candidates, never more.

## ja-JP quarter comment

Reproducing the exact ja-JP glyphs requires a CJK-capable font descriptor (`packages/chrona-fonts-noto-cjk`) and a Theme edited to reference `Noto Sans JP`; this was set up and confirmed the render pipeline accepts `--locale ja-JP` with that font, but `mission-light` + HALCYON‑1's own window does not happen to clip a quarter bucket, so the specific `Q1`/`Q3` loss was not re-triggered through this preset. The mechanism is already reproduced above (English) and in `test_replan_baseline_records_the_nonfitting_partial_quarter_label` (the same `axis-tier:2` quarter case the comment describes); wider ja-JP glyphs change only how visible the spurious loss is, not the code path (`format_axis_tier_label` and `thinning_schedule` have no locale branch, and a test already forbids one).
