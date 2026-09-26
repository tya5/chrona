# Design Plan — Axis Tier Appearance (#426)

**Public base:** `cd07bcd4` on `main`. **Source of truth:** [Issue #426](https://github.com/tya5/chrona/issues/426), Specification 39 (axis fitting and thinning), Specification 49 (semantic presentation contract), Specification 60 (declared colour scales). **Related:** #405/#406 (closed; settled which intervals appear and where — this issue is about how they look), #482 (thinning schedule, per-candidate; `layout/axis.py`), #483 (`axisBandDecoration` is `neutral` at opacity 1 in every shipped Theme). #466/#467 (annotation placement / lane rows) are owned by another dev session and are out of scope; #428 (View v0.23, as-of marker `date` form) is in flight from the lead and is the View version this issue's schema change follows.

## Published baseline, inference, and unverified facts

Reproduced by reading `cd07bcd4` (`.venv/bin/chrona render` against `examples/halcyon-1` was not needed to see the defect; it is structural, not data-dependent) and by inspecting `examples/halcyon-1/views/01-mission-brief.yaml`, which — like all 18 committed views — declares exactly one `band` tier (at the coarsest unit) and exactly two `labels` tiers:

```yaml
axis:
  tiers:
  - {unit: quarter, every: 1, role: band}
  - {unit: quarter, every: 1, role: grid-major}
  - {unit: quarter, every: 1, role: labels, label: {form: year-quarter, ...}}
  - {unit: month,   every: 1, role: labels, label: {form: short-month, ...}}
```

1. **A band tier fills the whole axis slot, not its own lane.** `layout/surface_composer.py` (band branch, current `compose_surface_layout`, ~line 1077-1088): every `role: band` interval's rect is `Rect(x, axis.bounds.block, x2-x, axis.bounds.block_size)` — the *axis slot's* block origin and size, unconditionally. Two band tiers would each emit a rect spanning the full slot and would exactly overlap; declaring a second one today does not even reach rendering, because of the next point.
2. **Every band shares one semantic id; the Theme role and the `_validate_background_shapes` overlap check are keyed off the literal string `"axisBandDecoration"`.** A second band tier would resolve the *same* Theme role as the first (same fill) and — since both would occupy the identical rect — trip `E_LAYOUT_BACKGROUND_OVERLAP` in `_validate_background_shapes` the moment the bound role is a `fill` at opacity < 1 (and would silently double-paint identically otherwise, per #483's opacity-1 neutral fill).
3. **Every labels tier shares one typography lookup, hoisted once outside the tier loop.** `axis_treatment = request.theme_tokens.text_treatment("axis")`, `axis_metrics = metric_for("axis")`, `axis_size = float(axis_treatment.font_size)` are computed once before the tier loop begins and reused for every `labels` tier's fit-measurement, lane height and `place_text(..., typography_role="axis", ...)` call. Two labels tiers cannot differ in size, weight or colour no matter what the Theme declares, because both consult the same three variables.
4. **`layout/surface_quality.py`'s host-validity check hardcodes the single id pair.** `if item.semantic_id == "axisLabel": allowed = isinstance(host, ShapePlacement) and host.semantic_id == "axisBandDecoration"` — a label hosted by any band id other than the literal `"axisBandDecoration"` string is rejected with `E_LAYOUT_TEXT_HOST_INVALID`. Any per-tier id scheme for bands must also touch this check, and the analogous `semantic_registry.py` bindings (`axisBandDecoration` → `theme_role="axis-band-decoration"`; `axisLabel` → `theme_role="axis"`, both single fixed constants).
5. **`axis_band_host` matches only on the inline (x) axis.** It picks the lowest-id band shape whose x-range contains a label's centre, with no block/lane test. Once bands can occupy different lanes, a quarter label's x-range can fall inside *both* a wide quarter band and a narrower month band beneath it; the current selection would not necessarily pick the band actually behind that label, which matters because `host_placement_id` feeds the text/host contrast check in `surface_quality.py` and `scene/perceptibility.py`.
6. **The View has no field to name any of this.** `schemas/view-v0.22.schema.yaml` axis tier items are `additionalProperties: false` with exactly `{unit, every, role, label}`; there is nowhere to bind a second Theme role or a per-tier typography role.
7. **`layout.axis.blockSize` is one Theme metric constant, not derived from the tier count.** `layout/sources.py::measure_sources` sizes the whole `timeline-axis` source from `metric["timeline.axis.blockSize"]` (a fixed per-Theme number, e.g. `timeline-axis-height`), independent of how many label/band tiers a View declares. It is the *ceiling* lanes must fit inside; it does not itself grow to fit new lanes. No change to this metric is needed for two tiers of the sizes the reference asks for, but a design that adds lanes must diagnose overflow against it rather than silently exceeding it.

## Literal issue acceptance ledger (copied verbatim)

1. A view can declare two `band` tiers and both render, each in its own lane, neither covering the other.
2. Two band tiers can take different fills from the Theme.
3. Two labels tiers can take different sizes, weights and colours.
4. One committed example renders a two-tier date band whose tiers are visually distinct, and reproduces byte-identically.

**Folded-in, non-literal (from the closed #405 thread):** "a band tier can resolve alternating fills from a Theme, and a committed slide shows it" — desirable, kept open architecturally (see design), not a criterion this phase must meet.

## Use cases and decisions to close

1. **Two bands, two lanes.** Decide the lane-assignment rule for `band`-role tiers. Chosen direction: an independent, monotonic per-role lane cursor (mirroring the one `labels` tiers already have), so a band tier's own declaration order among band-role tiers fixes its lane, with no coupling to interleaved `labels`/`grid-*` tiers. **Byte-identity carve-out:** when a View declares exactly one `band` tier (all 18 corpus views today), the rect keeps today's literal full-axis-slot geometry unchanged; the per-lane cursor only activates at two or more band tiers. This is a deliberate special case, flagged for architecture review.
2. **Distinct fills per band.** Decide the semantic-id scheme. Chosen direction: no View field. Layout assigns `axisBandDecoration` to the first declared band tier (unchanged) and `axisBandDecoration2`, `axisBandDecoration3`, … to subsequent ones, each a new fixed entry in the closed `semantic_registry.py` vocabulary (2-3 ordinals suffice for the target example; the vocabulary is closed by design, so a future author needing more registers more).
3. **Distinct typography per label tier.** Decide the View field. Chosen direction: one new optional field, `typographyRole` (string, an arbitrary Theme role key), on a tier — usable on a `labels` tier (selects the font *and*, through that role's `fontSize × lineHeight`, the lane height) and on a `band` tier (sizes its own lane only, inert when it is the sole band tier). Default omitted: `"axis"` — the role every corpus view already binds — so an unmodified View is byte-identical. This is a Layout-derived height, not a new numeric field, per the instruction to prefer deriving lane sizes from bound typography.
4. **Where the View field lands.** `axis.tiers[].typographyRole` in the View version immediately after the lead's v0.23 (#428); exact version number to be assigned by the lead in phase 2. No schema file is created in this phase.
5. **Host/contrast correctness under multiple lanes.** `axis_band_host` must additionally test block/lane overlap, not inline alone, so a label's host is the band actually behind it. `surface_quality.py`'s hardcoded `"axisBandDecoration"`/`"axisLabel"` string checks must generalize to the small closed id sets from decision 2 (and its label-side mirror, decision 6 below).
6. **Should labels get the same per-tier id treatment as bands?** Because `semantic_registry.py`'s `axisLabel` binding hard-codes `theme_role="axis"` and feeds the host-validity and contrast checks, and because two labels tiers now render with genuinely different roles, the design mirrors the band scheme: `axisLabel` (first labels tier, unchanged) / `axisLabel2` (second), etc. — even though the *font itself* is already resolved from the explicit `typographyRole` parameter, not from the registry constant.

## Responsibility and architecture review questions

- Layout owns axis geometry and typography resolution; View states intent (which role, if any) and never states a pixel height (Specification 33/43 ownership boundary; unaffected by this issue). Confirm the `typographyRole` field is intent, not measurement, and that Layout alone turns it into a lane size.
- Does the single-band byte-identity carve-out (decision 1) create a discontinuity an author can be surprised by when going from one band tier to two (a sudden height change from "whole axis" to "one line")? Record this explicitly as an authoring note, not a silent behavior change.
- Does generalizing `surface_quality.py`'s two hardcoded checks to closed id sets weaken the invariant they exist to enforce (that axis label text is only ever hosted by an axis band, never by an arbitrary shape)? Confirm the check should test "is one of the registered axis-band ids", not "is any shape".
- Interaction with #482 (`thinning_schedule`) and #483 (band opacity 1): neither is touched; thinning is per-candidate-label and independent of which lane/role a labels tier binds; #483's opacity-1 constraint applies per Theme role, so a second band's Theme role gets its own opacity-1 authoring discipline, not inherited from the first.
- Does this open a gap with the #405 wallboard/alternating-fill comment? State explicitly in the design whether it is met (it is not, in this phase) and where the extension point is left open.

## Ordered design slices and evidence needed

1. **Design.** This plan, plus `docs/design/issue-426-axis-tier-appearance-design-2026-09-26.md` and a Specification 39 amendment (new axis tier appearance section), published together.
2. **Architecture review** against Layout/View/Theme ownership, the #482/#483 interactions, and the byte-identity carve-out.
3. **Implementation plan** (phase 2): the schema field (version assigned by the lead), the per-role lane cursors, the id-ordinal scheme for bands and labels, the `axis_band_host`/`surface_quality.py` generalization, the derived Theme + new example view/slide, focused tests per literal criterion, and the full public-evidence regeneration with per-file attribution.

Issue acceptance needs a separate review with one row per literal criterion (this ledger), direct test and rendered-output evidence, the public-evidence batch diff, and the green CI matrix — written in phase 2, not this phase.
