# Design Plan — Axis Edge Label Thinning (#482)

**Public base:** `bf98f9b0` on `main`. **Source of truth:** [Issue #482](https://github.com/tya5/chrona/issues/482) and its ja-JP quarter comment; Specification 39 §1 (axis fitting); the [axis thinning record design amendment](../../design/issues-405-406-407-408-400-axis-thinning-record-design-amendment-2026-09-25.md) (#405–#408, #400); `src/chrona/presentation/layout/axis.py` and the axis section of `layout/surface_composer.py`. **Related:** #470/#471 (`mission-light` tuning that found both defects), #426 (axis tier appearance — out of scope, named not touched).

## Published baseline and reproduction

Reproduced on `bf98f9b0` with `chrona preset copy mission-light --output work/ml`, then `window: {mode: selected-planned, marginDays: 7}` and the month-label tier's `overflow: thin-with-record`, rendering `examples/halcyon-1/project.yaml --actual examples/halcyon-1/actual.yaml --preset work/ml/preset.yaml`.

1. **Uniform thinning for one collision.** The rendered scale is `domainStart: 2027-02-26 … domainEnd: 2027-11-26` (the `marginDays: 7` window clips 2027-03-05 back by 7 days). This leaves a 3-day partial February bucket, `axis-grid:4:0` to `axis-grid:4:1`, 11.45 px wide (`3 days × unitRatio 3.8168`). `axis_label_fits` correctly measures `"Feb"` as wider than 11.45 px and marks it `label_fits=False`. The scene then carries:
   ```
   W_LAYOUT_AXIS_LABEL_THINNED:axis-label:3:0:label-does-not-fit
   W_LAYOUT_AXIS_LABEL_THINNED:axis-label:3:2:thinning-stride
   W_LAYOUT_AXIS_LABEL_THINNED:axis-label:3:4:thinning-stride
   W_LAYOUT_AXIS_LABEL_THINNED:axis-label:3:6:thinning-stride
   W_LAYOUT_AXIS_LABEL_THINNED:axis-label:3:8:thinning-stride
   W_LAYOUT_AXIS_DENSITY:axis-tier:3:stride=2:phase=1
   ```
   Only `Mar, May, Jul, Sep, Nov` are placed; `Apr, Jun, Aug, Oct` (each ~114–118 px wide, holding a 3-character label of ~20–27 px) are dropped for no width reason of their own.
   - **Cause:** `thinning_schedule` (`axis.py`) searches, over the *whole* tier's candidate sequence, for the smallest `(stride, phase)` such that every candidate at that phase measures as fitting. A single non-fitting candidate at position 0 makes `stride=1` fail; no arithmetic progression can express "keep every position except 0", so the search is forced to `stride=2, phase=1`, which also drops every other position that fits perfectly well. This is a single global decision applied to the whole tier, not a decision scoped to the one collision.
   - The same code path already exists, unmodified, in the public corpus: `tests/integration/test_materialize_example.py::test_orion_gates_measures_the_colour_scale_legend_before_layout` and `::test_replan_baseline_records_the_nonfitting_partial_quarter_label` assert this exact `stride=2:phase=1` outcome today, on `examples/orion-asic` (`gates` context) and `examples/halcyon-1` (`07-replan-baseline`, an **explicit** window whose start clips the first quarter/month, not `marginDays`). The defect is not specific to `marginDays`; any clipped edge bucket triggers it.
2. **ja-JP quarter comment.** The reported case (`2027年Q1…`, keeping only `2027年Q2` and `2027年Q4`) is the same mechanism at the `quarter` tier: `test_replan_baseline_records_the_nonfitting_partial_quarter_label` already shows `axis-tier:2` losing position 0 to `label-does-not-fit` and positions 0/2 to the resulting `stride=2:phase=1` schedule in `en-US`. Wider ja-JP glyphs do not change the mechanism; they only make the one genuine failure (the clipped edge quarter) more likely and make the spurious loss of `Q1`/`Q3`-shaped positions more visible. No locale-specific code path exists to fix (`test_axis_label_path_has_no_language_code_branch` already forbids one); the fix belongs entirely to `thinning_schedule`.
3. **Sliver-month collision.** With the same window, setting the month tier's `overflow` to `visible-overflow` (`mission-light`'s current default) instead of `thin-with-record` renders the 11.45 px February label anyway and produces:
   ```
   W_LAYOUT_LABEL_OVERFLOW ... failureKind=label-collision ... placementId=axis-label:3:0
   W_SCENE_TEXT_INTERSECTION primitiveIds=[axis-label:3:0, axis-label:3:1] area=212.27
   ```
   a genuine rendered overlap between the February and March labels, confirming the issue's second report. Axis buckets from `axis_intervals` are contiguous and half-open (never overlapping each other), so a label that fits inside its own bucket cannot intrude on a neighbour; the existing per-candidate `axis_label_fits` self-containment check is therefore already a sufficient "does this label collide" predicate — the missing piece is only that `thin-with-record` must actually act on it per candidate, not per tier.
4. No code path validates or rejects `marginDays`; acceptance item 3 ("`marginDays` can be used by the presets without an axis warning") is a consequence of item 1: once thinning only removes the one genuinely non-fitting candidate, adopting `marginDays` on a `thin-with-record` tier produces exactly one honest diagnostic instead of a five-diagnostic flood, and the `mission-light` tuning notes' reason for avoiding margin (`docs/research/presentation/preset-tuning/mission-light/README.md`, items 2–3) no longer applies.

## Literal issue acceptance ledger

1. "`thin-with-record` removes only labels that collide. A test with one colliding edge label keeps all the others."
2. "A partial edge cell narrower than its label does not collide with its neighbour."
3. "`marginDays` can be used by the presets without an axis warning."

## Use case and decision to close

An author declares `overflow: thin-with-record` on an axis label tier and a window that clips an edge bucket (`marginDays`, or an explicit start/end). Exactly the candidates whose own measured label does not fit their own clipped interval are omitted; every other candidate is placed, regardless of its position's residue relative to any other dropped candidate. Decide:
- **Drop the periodic ("stride/phase") schedule search entirely** in favour of a direct per-candidate filter (retain iff `axis_label_fits`), because self-fit does not depend on any neighbour's disposition — a stride can never rescue a self-non-fitting candidate, and the issue's own bound ("at most... a stride to the colliding run") is satisfied a fortiori by never widening the drop set beyond the candidates that individually fail. This is the design's central, and only real, decision; it is stated in full in the design document for the owner to confirm or push back on.
- Retire the now-unreachable `reason="thinning-stride"` outcome and the `stride=`/`phase=` payload of `W_LAYOUT_AXIS_DENSITY` (they described a policy that no longer exists), while keeping the diagnostic code and the per-candidate `W_LAYOUT_AXIS_LABEL_THINNED:<id>:label-does-not-fit` evidence unchanged.
- Add one sentence to Specification 39 §1 extending "a clipped edge label that cannot fit is omitted; it does not reject an otherwise fitting level" from axis-level selection to `thin-with-record`'s per-label disposition, since the current implementation already violates this stated principle for interior labels sharing a residue class with a clipped edge.

## Responsibility and architecture review questions

- Layer ownership is unchanged: `thin-with-record` remains a deterministic Layout policy over completed interval outcomes (per the accepted amendment); this design only corrects its selection rule, not its inputs (`axis_intervals`, `axis_label_fits`), its diagnostics vocabulary, or Scene/adapter behavior.
- Does removing the stride search change `AxisThinningSchedule`'s public shape (`stride`, `phase` fields)? It must, since those fields describe a policy that no longer exists; `surface_quality.py`'s `AxisTierOutcome` invariant (`reason in {"label-does-not-fit", "thinning-stride"}` for a `thinned` disposition) needs the now-dead `"thinning-stride"` value removed at the same time.
- Is this compatible with #426 (axis tier appearance, differing per-tier roles)? Yes: the fix operates entirely within one tier's own candidate sequence and outcome list; it adds no cross-tier state and does not touch `AxisTierOutcome.role` or how tiers are styled relative to each other.
- Public evidence impact: `tests/integration/test_materialize_example.py`'s two assertions of the `stride=2:phase=1` diagnostic (orion-asic `gates`, halcyon-1 `07-replan-baseline`) will change, and both fixtures' rendered axis will show more month/quarter labels than today. This is the intended, and only expected, public-evidence change; the implementation plan must attribute it explicitly rather than treat it as incidental.

## Ordered design slices and acceptance evidence

1. **D482-1: design.** State the per-candidate retention rule, the retired `reason`/diagnostic payload, and the Specification 39 §1 addition. Publish `docs/design/issue-482-axis-edge-label-thinning-design-2026-09-26.md`.
2. **D482-2: architecture review.** Check the rule against Layout ownership, the `surface_quality.py` invariant, #426 compatibility, and the two affected public fixtures. Publish under `docs/reviews/current/`.
3. **D482-3: implementation plan.** Slices: `axis.py` (`thinning_schedule`/`AxisThinningSchedule`), `surface_composer.py` (the thin-with-record block and the density diagnostic), `surface_quality.py` (the invariant), tests (`test_axis_placement.py`, `test_materialize_example.py`), public evidence regeneration for the two affected fixtures plus a full 21-materializer batch to confirm nothing else moves.

Issue acceptance needs a separate review with one row per literal criterion, direct test and CLI evidence for both reproductions above, the attributed materializer diff, and the green CI run.
