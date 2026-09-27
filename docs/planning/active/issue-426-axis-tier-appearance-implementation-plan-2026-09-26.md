# Implementation Plan — Axis Tier Appearance (#426)

**Predecessor:** [Design](../../design/issue-426-axis-tier-appearance-design-2026-09-26.md), [Architecture review](../../reviews/current/issue-426-axis-tier-appearance-architecture-review-2026-09-26.md). **Gate:** do not start until the lead approves the design (§ unresolved items 1-3 of the review), including the View version number to author.

## Slice I426-1: View schema field

- **Owner/files:** new `schemas/view-v0.<N>.schema.yaml` (N given by the lead) forked from `view-v0.22.schema.yaml`, adding `typographyRole: {type: string, minLength: 1}` to the axis tier item's `properties`, keeping `additionalProperties: false`. Update `schemas/schema-inventory-v0.1.yaml` (mark v0.22 `transitioning` with `successor: view-v0.<N>.schema.yaml`, add the new `live` entry). Update `src/chrona/presentation/contracts/resources.py` consumer reference if it pins a literal version string.
- **Migration:** no existing View is required to change; the field is optional. No `removalSlice` needed for v0.22 beyond the normal transition bookkeeping (a following issue may retire it; not this one).
- **Tests:** schema-level: a tier with `typographyRole` validates; a `grid-major`/`grid-minor` tier with `typographyRole` is rejected (`additionalProperties: false` already enforces this by omission from that branch — add a schema test asserting the rejection, since this is new surface).

## Slice I426-2: semantic registry ordinals

- **Owner/files:** `src/chrona/presentation/model/semantic_registry.py` — add `axisBandDecoration2`, `axisBandDecoration3`, `axisLabel2`, `axisLabel3` bindings mirroring the existing `axisBandDecoration`/`axisLabel` entries' shape (`primitive_kind`, `purpose`, `scene_role`, `theme_role` suffixed `2`/`3`, no `contrast_class` change from the originals). `src/chrona/presentation/layout/surface_composer.py`: extend `BACKGROUND_SEMANTIC_IDS` with the two new band ids.
- **Tests:** a unit test asserting the registry has exactly these four new entries with the expected shapes (guards against silent registry drift, mirroring how the existing entries would be tested).

## Slice I426-3: lane cursors and per-tier typography

- **Owner/files:** `src/chrona/presentation/layout/surface_composer.py::compose_surface_layout`, axis tier loop (currently ~lines 911-1141):
  - Remove the single hoisted `axis_treatment`/`axis_metrics`/`axis_size` before the loop; compute them per tier from `tier.typography_role or "axis"` instead, for both `band` and `labels` branches.
  - Add a `band_lane_offset` cursor parallel to the existing `label_lane_offset`, advanced only by `band`-role tiers, with the single-band carve-out: if `sum(1 for t in axis_tiers if t.role == "band") == 1`, keep the current literal `Rect(x, axis.bounds.block, x2-x, axis.bounds.block_size)`; otherwise use `Rect(x, axis.bounds.block + band_lane_offset, x2-x, lane_size)` where `lane_size` is the same formula as the label lane's horizontal-orientation case.
  - Assign band semantic id by ordinal among band-role tiers (`axisBandDecoration`, `axisBandDecoration2`, `axisBandDecoration3`, raising a clear `LayoutError` if a fourth is declared, per the closed vocabulary).
  - Assign label semantic id by ordinal among labels-role tiers likewise, replacing the hardcoded `semantic_id="axisLabel"` at the `place_text`/`replace(...)` call.
  - Add an overflow diagnostic when `band_lane_offset` exceeds `axis.bounds.block_size` (mirror the existing `E_PRESENTATION_AXIS_OVERFLOW` class; exact id decided at review of this slice's diff, not pre-committed here).
- **Owner/files:** `axis_band_host` (same file) — add a block/lane containment test alongside the existing inline test, using each candidate band's own `bounds.block`/`block_size` against the label's placed baseline lane.
- **Owner/files:** `src/chrona/presentation/layout/surface_quality.py` — generalize the two hardcoded string checks (`E_LAYOUT_TEXT_HOST_INVALID` branch) to membership in the closed id sets from slice I426-2.
- **Tests (fail-before/pass-after per literal criterion):**
  - Criterion 1: two `band` tiers on a small synthetic View render two non-overlapping `ShapePlacement` rects (`Rect.block`/`block_size` disjoint, asserted directly).
  - Criterion 2: same View with a Theme binding `axisBandDecoration`/`axisBandDecoration2` to two distinct fills — assert the two rects' resolved paint differs.
  - Criterion 3: two `labels` tiers with distinct `typographyRole`s bound to distinct Theme roles (different `fontSize`, `fontWeight`, and a `colorBindings` fill) — assert the two `TextPlacement`s' resolved treatment and paint differ.
  - Single-band carve-out: an unmodified existing View's `ShapePlacement` for its one band tier is byte-identical to `cd07bcd4`'s output (structural Scene comparison, not just "renders").
  - `axis_band_host`/contrast: a label whose lane matches the *second* band, not the widest-by-x one, resolves `host_placement_id` to the second band; `surface_quality.py` does not raise `E_LAYOUT_TEXT_HOST_INVALID` for either label/band pair.
- **Focused tests to run:** `tests/unit/chrona/presentation`, `tests/integration`, `tests/cli` (per the brief), plus any axis-specific test module found under `tests/unit/chrona/presentation/layout` at implementation time.

## Slice I426-4: committed example and public evidence

- **Owner/files:** one new slide (or the existing slide under a derived Theme — decided when this slice starts, per design §3) declaring the two-tier band from design §4, plus the derived Theme's new roles and fills.
- **Evidence:** `tools.regenerate_public_examples --write --jobs 6` then `--check`; attribute every changed file — expect exactly the new/changed example's Scene and rendered outputs to differ, and no other public materializer to move (the single-band carve-out is what makes this the expectation, not a hope).
- **Refresh:** `tools/diagnostic_inventory.py`, `tools/presentation_contrast.py`, `tools/presentation_font_identity.py`, `tools/presentation_coverage.py` (no `--check` first), then `conformance/run_conformance.py`.
- **Before/after PNG crops** of the new example's axis region (resvg_py + PIL), visually confirming two visually distinct lanes (fill and type), per the brief's user-visible-change rule.
- **Acceptance test corpus counts:** check `tests/acceptance/output/test_public_geometry_regressions.py` for hardcoded public-slide/axis-label counts; update deliberately if the new example adds to the corpus, and explain the change in the slice review.

## Slice I426-5: reviews

- Draft the implementation/slice review(s) and the literal-acceptance review (one row per criterion in the design plan's ledger, `met`/`deferred`/`not met` with direct evidence), `CI: pending` for the lead to fill in. Explicitly record the #405 fold-in criterion as `deferred` with the successor-issue pointer from design §6.

## Publication order

I426-1 → I426-2 → I426-3 (code + tests) → I426-4 (evidence) → I426-5 (reviews), each its own commit, per the brief's phase-2 process.
