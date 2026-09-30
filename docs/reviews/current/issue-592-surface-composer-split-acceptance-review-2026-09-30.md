<!-- chrona:literal-acceptance/v1 -->

# Issue #592 — surface composer split acceptance review

Source: [Issue #592](https://github.com/tya5/chrona/issues/592), observed 2026-09-30. Design and slices: [design plan](../../planning/active/issue-592-surface-composer-split-design-plan-2026-09-29.md) and [implementation plan](../../planning/active/issue-592-surface-composer-implementation-plan-2026-09-29.md). Slices, all on `main`: I592-1 PR [#614](https://github.com/tya5/chrona/pull/614), I592-2 PR [#621](https://github.com/tya5/chrona/pull/621), I592-3 PR [#627](https://github.com/tya5/chrona/pull/627), I592-4 PR [#636](https://github.com/tya5/chrona/pull/636), I592-5a PR [#647](https://github.com/tya5/chrona/pull/647), I592-5b PR [#648](https://github.com/tya5/chrona/pull/648), I592-6 PR [#649](https://github.com/tya5/chrona/pull/649).

## Literal issue acceptance

### Issue #592

- Source: [Issue #592](https://github.com/tya5/chrona/issues/592)
- Observed: 2026-09-30

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | `surface_composer.py` contains orchestration only, under about 400 lines. Each concern module has a docstring naming what it owns and what it reads. | met | [`surface_composer.py`](../../../src/chrona/presentation/layout/surface_composer.py) is **294 lines** (3,457 at filing). It builds each phase's typed input, runs the phases in the published order and hands every batch to one completion call. It still holds three small coordination pieces: the obstacle-index seeding and its `register_*` helpers (the composer owns the one shared index), nine lines resolving text visuals between annotations and completion, and `timeline_content_block_requirement`, the public row-extent helper that `render_review` calls. Each of the 16 surface modules named in [Spec 33 §8.3](../../specification/33-intent-oriented-layout.md) opens with a one-line docstring of the form "Owns …; reads …", and the composer says "Coordinates …; reads …". [`test_surface_module_ownership.py`](../../../tests/unit/tools/test_surface_module_ownership.py) (PR [#651](https://github.com/tya5/chrona/pull/651)) fails if a named module is missing, lacks that docstring, or the composer reaches 400 lines. | — |
| 2 | Every public materializer and Scene is byte-identical, and the full test suite passes unchanged. | met | All 29 public Scene and SVG pairs are byte-identical at the end state: `tools.regenerate_public_examples --check` passed on `d1732011` (29 slides), and every slice's exact-main three-OS run is green: I592-3 [36647931251](https://github.com/tya5/chrona/actions/runs/36647931251), I592-4 [36652826531](https://github.com/tya5/chrona/actions/runs/36652826531), I592-5a [36661040253](https://github.com/tya5/chrona/actions/runs/36661040253), I592-5b [36663561172](https://github.com/tya5/chrona/actions/runs/36663561172), I592-6 [36665890946](https://github.com/tya5/chrona/actions/runs/36665890946), and PR #651 [36666797776](https://github.com/tya5/chrona/actions/runs/36666797776). The suite passes with **no assertion changed**, but not literally "unchanged": since the design base `b7dfd726`, 12 pre-existing test files were edited only to follow moved private helpers (an import path, a call target, or a monkeypatch target such as the as-of candidate search) or to unpack a typed batch, and new tests were added; the `test_schema_inventory.py` change in that range belongs to #591. The byte gate caught one defect the unit tests missed (a local `lane_emissions` shadowing the moved function, I592-6). | — |
| 3 | The module reachability gate covers the new modules. | met | `tools/check_module_reachability.py` walks every module under `src/chrona`; on `d1732011` it reports 128 modules reachable, 0 staged, none orphaned, and `conformance/run_conformance.py` runs it as `module-reachability`. [`test_surface_module_ownership.py`](../../../tests/unit/tools/test_surface_module_ownership.py) additionally asserts that each module named in the Spec 33 table is in the gate's module set. `check_import_direction.py` (9 packages, 33 edges, all inward) also passes. | — |
| 4 | Ownership notes are added to spec 33 (Layout ownership), so future issues can name the module they touch. | met | [Spec 33 §8.3](../../specification/33-intent-oriented-layout.md) lists all 16 surface modules with their responsibility, states that shared mutable state is limited to the obstacle index, and records the one-directional calendar join between axis and backgrounds; the table is now tied to the code by the ownership test above. | — |

## Programme-level criteria (optional)

None.

## Architecture and release conclusion

The split is private to Layout: no schema, resource, Scene, adapter or diagnostic identifier changed, and Layout, Scene and adapters keep their #466 and #467 obstacle and phase order (label, route and annotation phases receive the one `SurfaceObstacleIndex`; legend, content and completion take none). Each extraction slice added a wiring test for its phase order. The generated `diagnostic-inventory` moves with the code and is regenerated by the main sync, per #590.

Residuals, not blocking this issue: the composer's nine lines of text-visual resolution could join `surface_visuals`, and `timeline_content_block_requirement` could move next to the row-extent code it calls. The exact-main three-OS run for the commit that publishes this review is cited in the closing comment.
