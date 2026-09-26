# Design — Axis Edge Label Thinning (#482)

**Status:** proposed for whole-architecture review. **Plan:** [design plan](../planning/active/issue-482-axis-edge-label-thinning-design-plan-2026-09-26.md). **Evidence:** [reproduction evidence](../research/presentation/issue-482-axis-edge-label-thinning-prototype-evidence-2026-09-26.md). **Authorities:** Specification 39 §1/§1.1 (amended in this commit); the [axis thinning record design amendment](issues-405-406-407-408-400-axis-thinning-record-design-amendment-2026-09-25.md) (#405–#408, #400), whose "smallest positive thinning stride" rule this document corrects.

## Use case

An author declares `overflow: thin-with-record` on an axis label tier and a window that clips an edge bucket (`marginDays`, or an explicit `start`/`end`). Exactly the candidates whose own measured label does not fit their own clipped interval are omitted. Every other candidate is placed, however that candidate's position relates to any other omitted candidate.

## Root cause

`thinning_schedule` (`src/chrona/presentation/layout/axis.py`) searches over the whole tier's ordered candidate sequence for the smallest `(stride, phase)` such that *every* candidate at that phase measures as fitting:

```python
def thinning_schedule(label_fits: tuple[bool, ...]) -> AxisThinningSchedule:
    for stride in range(1, len(label_fits) + 1):
        for phase in range(stride):
            retained = tuple(index for index in range(phase, len(label_fits), stride))
            if retained and all(label_fits[index] for index in retained):
                return AxisThinningSchedule(stride, phase, retained)
    raise ValueError("E_PRESENTATION_AXIS_OVERFLOW")
```

A single non-fitting candidate at position 0 (the usual case: a window-edge bucket clipped to a few days) makes `stride=1` fail. No arithmetic progression can express "keep every position except 0", so the search is forced to the next stride that happens to avoid position 0 — typically `stride=2, phase=1` — which also removes every other candidate sharing that phase, regardless of whether it fits. This is a single global decision applied to the whole tier from one local failure. The reproduction evidence shows it removing `Apr, Jun, Aug, Oct` from a 10-month HALCYON‑1 axis to avoid one clipped February bucket, and the same mechanism already exists, unmodified, in two published fixtures (`examples/orion-asic` `gates`, `examples/halcyon-1` `07-replan-baseline`).

Self-fit does not depend on any other candidate: `axis_label_fits` measures one candidate's label against that candidate's own clipped interval width, computed once per candidate before thinning runs. Dropping or keeping a *different* candidate never changes whether *this* candidate's label fits its own bucket. A stride can therefore never rescue a self-non-fitting candidate; the only thing a stride ever accomplishes today is discarding additional, otherwise-fitting candidates to make a uniform pattern possible.

Axis buckets from `axis_intervals` are contiguous, non-overlapping, half-open intervals covering the window. A label that stays within its own bucket cannot reach a neighbour's bucket. The reproduction evidence confirms the converse directly: rendering the same clipped February bucket under `visible-overflow` (instead of `thin-with-record`) produces a real, geometry-checked `W_SCENE_TEXT_INTERSECTION` between the February and March labels. Self-containment is therefore both necessary and sufficient evidence of "this label would collide with its neighbour" for this design; no separate two-label geometric collision check is needed.

## Contract: per-candidate retention

**Owner: Layout**, unchanged from the accepted amendment — `thin-with-record` remains a deterministic policy over the completed, ordered label interval outcomes of one axis tier; it never changes calendar buckets, label text, `every`, or Scene geometry.

`thinning_schedule` is replaced by a direct filter:

```python
@dataclass(frozen=True)
class AxisThinningSchedule:
    """Deterministic retained/thinned positions for one measured label sequence."""
    retained_positions: tuple[int, ...]
    thinned_positions: tuple[int, ...]

def thinning_schedule(label_fits: tuple[bool, ...]) -> AxisThinningSchedule:
    retained = tuple(index for index, fits in enumerate(label_fits) if fits)
    if not retained:
        raise ValueError("E_PRESENTATION_AXIS_OVERFLOW")
    thinned = tuple(index for index, fits in enumerate(label_fits) if not fits)
    return AxisThinningSchedule(retained, thinned)
```

- A candidate that fits is always retained. `thin-with-record` never drops a fitting candidate to preserve a uniform rhythm.
- A candidate that does not fit is always thinned, with the single, already-existing reason `label-does-not-fit`. The `reason="thinning-stride"` outcome is retired: it described a candidate dropped only to satisfy a periodic pattern, and no candidate is ever dropped for that reason under this rule.
- If no candidate fits at all, thinning still cannot legally remove every interval (unchanged invariant from the accepted amendment); the existing fallback in `surface_composer.py` — place the complete, visible result with the measured `reason` — is unchanged.
- `stride`/`phase` are removed from `AxisThinningSchedule`'s public fields; nothing in the corrected rule computes or needs them. `surface_composer.py`'s call site (`schedule.retained_positions`) and its `W_LAYOUT_AXIS_DENSITY` diagnostic change from `stride=<n>:phase=<n>` to a payload describing what actually happened, for example `thinned=<count>` naming the thinned candidate ids already carried individually by `W_LAYOUT_AXIS_LABEL_THINNED`. The diagnostic *code* is unchanged; only its payload, which described a policy that no longer exists, changes.
- `surface_quality.py`'s `AxisTierOutcome` invariant (`item.disposition == "thinned" and item.reason not in {"label-does-not-fit", "thinning-stride"}`) drops `"thinning-stride"` from the allowed set, so a manifest can no longer claim a disposition the corrected rule never produces.

### Why not a stride scoped to the colliding run

The issue allows, at most, a stride local to "the colliding run" (the contiguous block of non-fitting candidates). Because self-fit is fixed per candidate and independent of neighbours, a stride within a run of already-failing candidates cannot rescue any of them — every member of a colliding run individually fails to fit, so every member is, by the issue's own rule ("removes only labels that collide"), a label that must be removed. Retaining a stride-selected subset of a failing run would keep a label that still does not fit its own bucket, which is exactly the collision the issue reports. The corrected rule (drop exactly the non-fitting set, nothing more) is therefore the loosest policy the issue's own bound permits, not an arbitrary simplification. **This is the design's one real decision; it is stated here in full for the owner to confirm.** If a future case is found where a genuinely uniform, non-edge-driven density reduction is wanted for its own sake (for example, many day-level ticks that are all individually too narrow for their label but the axis would look better showing every Nth), that is a distinct, additive feature — a declared density policy, not a thinning correction — and is out of scope here.

### ja-JP quarter comment

The reported case is the same mechanism at the `quarter` tier (`test_replan_baseline_records_the_nonfitting_partial_quarter_label` already exercises `axis-tier:2` losing position 0 to a clipped edge quarter, in `en-US`, with today's buggy `stride=2:phase=1`). `format_axis_tier_label` and `thinning_schedule` have no locale branch (`test_axis_label_path_has_no_language_code_branch` enforces this), and the corrected rule does not add one: wider ja-JP glyphs only make the one genuine edge failure more likely to occur and more visible when it does; they do not change which candidates are retained once the rule is per-candidate.

## Migration and compatibility

- No schema, View, or Theme syntax change. `overflow: thin-with-record` keeps its declared name and meaning ("Layout drops what does not fit and records why"); only the selection rule inside that meaning is corrected.
- Specification 39 gains §1.1, extending the existing "a clipped edge label ... does not reject an otherwise fitting level" principle from axis-level selection to the `thin-with-record` per-label disposition, and one acceptance bullet in §4. This states normatively what the corrected code does; it is not a new capability.
- **Public evidence:** `examples/orion-asic` (`gates`) and `examples/halcyon-1` (`07-replan-baseline`) both currently render fewer axis labels than they should (see reproduction evidence); both change to show every non-clipped label. This is the intended output change, attributed in the implementation plan, not an incidental one. No other public fixture is expected to have a clipped edge bucket under `thin-with-record` today; the batch regeneration confirms this.
- `AxisThinningSchedule.stride`/`.phase` are a Layout-internal dataclass, not part of any public schema; removing them has no schema or Scene impact.

## Diagnostics

- `W_LAYOUT_AXIS_LABEL_THINNED:<candidate-id>:label-does-not-fit` — unchanged, one per genuinely non-fitting candidate.
- `W_LAYOUT_AXIS_DENSITY:axis-tier:<tier>:thinned=<count>` — payload corrected; still one line per tier where thinning occurred, still the required evidence a reader cannot recover from the picture alone, no longer implying a periodic pattern that does not exist.
- No new diagnostic code.

## Tests

- `thinning_schedule((False, True, False, True))` now returns `retained_positions=(1, 3)`, `thinned_positions=(0, 2)` — both non-fitting positions dropped, both fitting positions kept (the existing test in `test_axis_placement.py` asserted `stride`/`phase`; it is corrected to assert the new fields).
- One colliding edge label among many fitting ones (the HALCYON‑1/`marginDays` reproduction): only the clipped candidate is thinned; every other candidate is placed.
- A partial edge cell narrower than its label produces no `W_SCENE_TEXT_INTERSECTION` between adjacent axis labels (covers the sliver-month collision directly).
- `marginDays` with `thin-with-record` produces exactly one `W_LAYOUT_AXIS_LABEL_THINNED` (for the clipped bucket) and no others.
- All-non-fitting fallback (existing behavior) is unchanged: a tier where no candidate fits still raises the same `E_PRESENTATION_AXIS_OVERFLOW`-guarded fallback, not a silent empty tier.
- `test_orion_gates_measures_the_colour_scale_legend_before_layout` and `test_replan_baseline_records_the_nonfitting_partial_quarter_label` are updated to the corrected diagnostics and gain an assertion that the previously-dropped fitting labels (`axis-label:3:2`, etc.) are now present.
