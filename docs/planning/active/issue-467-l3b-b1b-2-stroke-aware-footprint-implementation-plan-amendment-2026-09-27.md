# Implementation Plan Amendment — #467/#494 B1b-2 Stroke-Aware Footprint Seam

**Base:** public `09bd2661` (2026-09-27). **Predecessors:** [B1b-2 design plan](issue-467-l3b-b1b-2-stroke-aware-footprint-design-plan-2026-09-27.md), [design correction](../../design/issue-467-l3b-b1b-2-stroke-aware-footprint-correction-2026-09-27.md), [miter-envelope amendment](../../design/issue-467-l3b-b1b-2-miter-envelope-amendment-2026-09-27.md), [architecture review](../../reviews/current/issue-467-l3b-b1b-2-stroke-aware-footprint-architecture-review-2026-09-27.md), and [miter review amendment](../../reviews/current/issue-467-l3b-b1b-2-miter-envelope-architecture-review-amendment-2026-09-27.md). This plan authorizes only the independently publishable B1b-2 direct seam; it does not activate lane mode or implement B2/B3/L3c.

## Slices

### S1 — Layout geometry closure and ownership migration

Move construction of selected mark and icon geometry out of Scene into Layout, before obstacle allocation. Add/extend a Layout-owned geometry module (planned `src/chrona/presentation/layout/lane_mark_geometry.py`) that consumes canonical Theme/icon metrics and returns immutable completed paths plus geometry-only visible extents. Move/replace Scene-side `_symbol_primitives` use of `ThemeTokenView.variant_symbol`, `mark_geometry.symbol_geometry`/`glyph_parts`, and `_complete_icon_paths` in `src/chrona/presentation/scene/v05_builder.py`. Preserve exact bytes/semantics: point and point-legend swatches; glyph contain-center; built-in diamond outline override but glyph ignores that override; `paint:none` omission; part order and IDs; close-point conversion and float arithmetic; vector cap/join and scaled stroke; raster viewport; normalized icon path order and IDs. Scene continues selecting identity/order and invoking `ScenePaintResolver`; it receives complete Layout geometry and resolved paints, with no post-resolution paint mutation or geometry derivation. `ScenePaintResolver` remains sole paint conversion.

Layout may ask `ThemeTokenView` only for validated semantic stroke-binding presence (e.g. add a query alongside `variant_symbol` in `src/chrona/presentation/model/theme_tokens.py`); it must not inspect resolved color or convert paint. Test absent vs present optional stroke channels for roles whose solid fill can exist without a stroke, so expansion follows binding presence rather than guessed role names. Theme value validation/diagnostics remain authoritative. Resolved Theme/icon stroke width is used once: rectangles expand by half-width; segments keep centerline plus one `ObstacleSegment.stroke_width`; stroked path control-point envelopes expand by **10× stroke width per side**; fill-only paths do not expand. Clearance is separate. No schema/resource migration is expected.

Primary owners/tests: `src/chrona/presentation/layout/` geometry module, `src/chrona/presentation/model/theme_tokens.py`, `src/chrona/presentation/scene/v05_builder.py`; extend `tests/unit/chrona/presentation/layout/` and `tests/unit/chrona/presentation/model/test_theme_tokens.py`, and add direct geometry parity/identity tests. Retain and extend `tests/unit/chrona/presentation/scene/test_v05_builder.py`, `test_mark_geometry.py`, and `test_paint.py` as characterization/compatibility tests, not as alternate geometry owners. Add static/module-reachability assertion that geometry/path builders are not imported by Scene.

### S2 — Projection-to-atomic-bundle mapper

Add a Layout-only mapper (planned `src/chrona/presentation/layout/lane_bundle_mapper.py`) from `ReviewProjection` plus lane intent, resolved Theme/icon metrics, text measurements and temporal scale into complete immutable `LaneCandidate`/`LaneMember` bundles consumed by `lane_allocation.py`. Integrate at the existing preflight/layout boundary in `surface_composer.py`; do not place the mapper in usecase projection, Scene, or the neutral allocator. Include each source member once with stable IDs; represent planned, snapshot/scenario comparison, closed/open/point/missing Actual, progress, attached-point and selected icon geometry; declare only approved within-bundle mark overlay pairs, never exempt labels. Preflight and eventual final composition must share the same completed geometry inputs. Missing/invalid geometry or metrics fail closed before allocation using the approved stable Layout/Theme diagnostic; never omit an incomplete mark. Lane mode remains guarded/fail-closed after this slice.

Tests: new `tests/unit/chrona/presentation/layout/test_lane_bundle_mapper.py` for every design matrix row and direct Layout-geometry/footprint parity; optional-stroke channel presence; segment endpoints/caps; miter envelope; glyph/icon/vector/raster/legend geometry; overlays/IDs/order; double-count prevention; failure diagnostics; stable ordering. Extend `test_lane_preflight.py` and `test_lane_allocation.py` for mapper-to-allocator atomic bundle closure, and add focused composition fixture tests around `resolve_mark_visual_requests` / existing composer entry points. No `Project`, `View`, or `Scene` dependency is added to the neutral allocator.

## Evidence, gates, publication

- **Miter gate:** the conservative 10× width-per-side envelope is fixed by the published amendment. Run real current `02-programme-board` lane feasibility with this bound; **≤12 lanes and the required chain remain hard gates**. If the bound fails, stop and return to design; do not relax ≤12, use target-specific lane allocation, or change adapter/ScenePaint policy.
- **Byte and geometry characterization:** capture automatic and explicit Scene plus SVG bytes before/after; compare path commands, identity/order, paint and dimensions. Include built-in point shapes, multi-part glyphs, point legend variants, vector icons, and material-icons SVG. Record expected byte changes (geometry ownership refactor should preserve existing outputs); any unexplained diff blocks acceptance. Exercise invalid/missing metrics and confirm deterministic fail-closed diagnostics.
- **Public materializer batch:** render the focused corpus through SVG, PNG, PDF, Typst and TikZ adapters where supported; Typst general-path rejection is expected and is not evidence for path rendering. Inspect generated SVG/Scene and raster/PDF/TikZ outputs as a batch. Confirm unchanged paint serialization and no adapter geometry repair. Record artifact hashes/diffs and exact commands in the slice review.
- **Resources/schemas:** no View/Theme/Scene schema, preset, resource mirror, or generated schema change is intended. If implementation requires one, stop and amend the plan/design first. Include package/resource integrity checks even when no resource changes are expected.
- **Focused CI:** run targeted Layout/Theme/Scene tests and static ownership checks locally. At publication, use CI for the repository's three-OS full pytest/conformance, wheel/smoke, and newest-Python public-materializer matrix; inspect all checks and document unrelated failures. Do not duplicate the full local matrix without a concrete risk.
- **Publication boundary:** publish S1 and S2 as separately reviewable commits/reviews if ownership migration is independently safe; otherwise publish one B1b-2 commit with explicit staged boundaries. Each review names commit, commands, generated artifact comparison, gate result, and all nine literal criteria below as `deferred` for this seam. Do not claim public acceptance or enable lanes. B2 one-plan composition, B3 route-cause integration, and L3c public activation remain later work.

## Literal issue acceptance criteria (all deferred by B1b-2)

### #467

- [ ] A lane row mode exists. On `02-programme-board` the 26 items occupy at most 12 lanes, with the chain `structure → avionics → bus-test` on one lane.
- [ ] Every packed task and milestone has a visible name on the slide; no `W_LAYOUT_LABEL_SUPPRESSED` for a packed item on any committed slide.
- [ ] Lane assignment is deterministic, and a test shows that one inserted item does not reorder unrelated lanes.
- [ ] Deltas remain visible for packed items that have them.
- [ ] New Views and the packaged presets default to lanes; `automatic` still renders exactly as today.
- [ ] At least three committed slides use lanes (for example `01`, `02` and `06`), and their evidence is reproducible.

### #494

- [ ] On `02-programme-board` (lanes), no relation is suppressed for `egress-collision`, and every remaining suppression is listed with a measured cause.
- [ ] `test_lane_relation_routes_never_cross_a_required_lane_label` still passes on 02, 11 and 12: no route crosses any lane or member label.
- [ ] Lane count and lane membership on 02 are unchanged, or any change is attributed.
