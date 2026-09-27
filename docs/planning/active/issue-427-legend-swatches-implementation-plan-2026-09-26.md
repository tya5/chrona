# Implementation Plan — Legend Swatches and Arrangement (#427)

**Public design base:** the commit that publishes the [architecture review](../../reviews/current/issue-427-legend-swatches-architecture-review-2026-09-26.md). **Authority:** [design](../../design/issue-427-legend-swatches-design-2026-09-26.md), Specifications 33 and 49, [Issue #427](https://github.com/tya5/chrona/issues/427).

## Literal acceptance ledger

1. A milestone legend entry renders as the symbol the Theme binds for milestones, at the size the chart draws it.
2. An outline-only mark, a dashed line and a relation terminal each have a legend key that shows them.
3. A layout profile can declare a horizontal legend, and one committed example renders one.
4. No legend entry's appearance is decided by `surface_composer` arithmetic that a document cannot reach.
5. A scale entry shows the entity's declared title when one exists.
6. Swatch and label take separate theme roles.

## Coordination

No other open issue owns these files. #479/#421 read `legend_entries`/Detail Profile/Layout Profile as already-typed resources and are not touched. Before push, fetch `origin/main` and check ahead/behind; stop on a conflict in `layout/surface_composer.py`, `scene/v05_builder.py`, `model/semantic_registry.py`, or `schemas/schema-inventory-v0.1.yaml`.

## I427-1: schema and registry additions

**Owners/files:**
- `schemas/theme-v0.13.schema.yaml`: copy of `theme-v0.11.schema.yaml` with `swatchInlineSize` added to the per-role property list.
- `schemas/layout-profile-v0.10.schema.yaml`: copy of `layout-profile-v0.9.schema.yaml` with `direction`, `gap`, `itemMinInlineSize` added to `$defs/slot`, required via `if`/`then` when `source: legend`.
- `schemas/schema-inventory-v0.1.yaml`: `theme-v0.11` → `state: transitioning, successor: theme-v0.13.schema.yaml`; add `theme-v0.13` as `state: live`; `layout-profile-v0.9` → `state: transitioning, successor: layout-profile-v0.10.schema.yaml`; add `layout-profile-v0.10` as `state: live`.
- `model/semantic_registry.py`: `legendEntry.theme_role` → `"legend-swatch"`; split `legendLabel` into its own row if not already distinct; no `primitive_kind`/`purpose` change.
- `presentation/contracts/resources.py`: accept both Theme versions and both Layout Profile versions during the transition, per the existing multi-version loader pattern.

**Focused tests:** schema-validation fixtures for both new schemas (valid/invalid `direction`/`gap` combinations; valid/invalid `swatchInlineSize`); a loader test that a v0.9 Layout Profile and a v0.11 Theme still validate; registry test that `legendEntry`/`legendLabel` resolve to distinct theme roles.

**Gate:** focused tests only (no product behavior yet).

## I427-2: Layout builds the swatch geometry

**Owners/files:**
- `layout/surface_composer.py`: replace the fixed `swatch_size`/vertical-stack block (`:1739-1784`) with per-entry dispatch on `semantic_binding(role).primitive_kind`:
  - `mark`: build a `MarkPlacement` via the existing `place_mark`-style geometry (`mark_geometry(role)`, `rounded_diamond_path` for a point role), height from `role.markHeight × metric_values["timeline.mark.blockSize"]`, inline length from `theme_tokens.number("legend-swatch", "swatchInlineSize")` for a span shape (point roles are square from their own geometry).
  - `line`: build a `RelationPlacement` (short elbow with `marker(role)`, or a straight dashed segment for `asOf`/axis-grid roles), length from `swatchInlineSize`, `strokeWidth`/`dash` from the role.
  - `decoration`: build a `ShapePlacement` sized `swatchInlineSize × (role height ratio × timeline.mark.blockSize)`, background/pattern from the role.
  - `direction`/`gap`/`itemMinInlineSize` resolution for the slot: `block` keeps the current stacking formula (now driven by `gap` instead of `legend_step`); `inline` lays swatch+label pairs left to right and wraps at `itemMinInlineSize`, growing the slot's block size by wrapped-line count.
- `layout/surface_quality.py`: no new dataclass; reuse `MarkPlacement`/`RelationPlacement`/`ShapePlacement`.

**Focused tests:**
- a milestone legend entry's `MarkPlacement` bounds equal a real milestone mark's bounds computation on the same theme/metrics;
- an outline-pattern role's legend `ShapePlacement`/paint resolves to `fill: none`;
- a `dependency` legend entry is a `RelationPlacement` with the role's `marker_end`; `dependency-critical` differs only in resolved `strokeWidth`;
- `direction: inline` places entries left to right and wraps at `itemMinInlineSize`; `direction: block` matches today's stacked order;
- a v0.9 legend slot (no `direction`/`gap`) still lays out with the historical formula.

**Gate:** `tests/unit/chrona/presentation`, `tests/integration`.

## I427-3: Scene reuses the per-kind emission it already has

**Owners/files:**
- `scene/v05_builder.py`: factor the mark loop's Symbol/Rect choice (`:339-396`) into `_mark_scene_primitive(...)`, called both from the per-item loop and from a new loop over `placed_surface.marks` whose `placement_id` starts with `legend-swatch:`. Remove the hardcoded `PrimitiveKind.RECT` legend branch (`:474-478`); route `line`/`decoration`-kind legend entries through the existing relation loop (`:462-470`) and decoration loop (`:332-338`) respectively, tagging a legend relation `source_kind="legend"`.
- `review/v05_content.py`: `scale_entries` label becomes `project.get("entities", {}).get(value, {}).get("title", value)`.

**Focused tests:**
- a milestone legend primitive is `Symbol` with the theme-bound shape;
- an outline-pattern/dashed-role legend primitive carries the role's pattern/dash;
- a colour-scale entry's label is the entity title when declared, the raw value otherwise;
- the `scale_paints` override still applies only to `scale:`-prefixed relations/marks, not to the new legend-relation `source_kind="legend"` path generally.

**Gate:** as I427-2, plus `tests/cli`.

## I427-4: evidence — migrate one profile, add a horizontal legend to another

**Owners/files:**
- `examples/halcyon-1/layouts/wallboard.yaml`: bump to `chrona/layout-profile/v0.10`; declare the `legend` slot's `direction: block`, `gap` (matching today's `legend_step` visually as closely as the new formula allows — any residual pixel shift is expected and inspected, not suppressed).
- `examples/halcyon-1/themes/wallboard.yaml`: add a `legend-swatch` role (`swatchInlineSize`, plus any pattern/marker already implied by existing roles).
- `examples/halcyon-1/layouts/print-portrait.yaml`: bump to v0.10; add a `legend` slot with `direction: inline`, `gap`, `itemMinInlineSize`.
- `examples/halcyon-1/themes/print.yaml`: add a `legend-swatch` role.
- `examples/halcyon-1/profiles/detail.yaml` (or a new profile for `03-launch-campaign` if reuse would change `02-programme-board`'s entries): add legend entries for `planned` (already outline-pattern in `print.yaml`), `dependency`, and `asOf`.
- `examples/halcyon-1/contexts/03-launch-campaign.yaml`: wire the new legend-bearing detail/layout profiles.

**Public evidence:** `tools.regenerate_public_examples --write --jobs 6`, then `--check`. Expected diffs: `02-programme-board` (legend swatch shape/size only), `03-launch-campaign` (new legend primitives). Attribute every other changed file/diagnostic as a defect. Render before/after PNG crops of both legends and inspect: milestone diamond shape, outline `planned` key, dashed `asOf` key, `dependency` arrowhead, horizontal wrapping.

**Gate:** full focused test set, `conformance/run_conformance.py`, `diagnostic_inventory.py`/`presentation_contrast.py`/`presentation_font_identity.py`/`presentation_coverage.py` refreshed if stale, the 21-materializer batch, then push and the four-job CI. The slice review is published separately.

## I427-5: issue acceptance

A separate acceptance review under `docs/reviews/current/`, one row per literal criterion above, direct test and rendered-output evidence, the batch materializer diff, and the green CI run. Close #427 (and confirm #422's merged criteria are covered) only then.

If a slice exposes a Theme whose real mark geometry cannot produce a sane legend swatch (e.g. a zero-height role), a wrap threshold that never wraps, or a conflict with #479's preset loading, pause, publish a design correction, and amend this plan.
