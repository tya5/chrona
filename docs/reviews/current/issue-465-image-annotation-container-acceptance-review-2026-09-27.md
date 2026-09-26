<!-- chrona:literal-acceptance/v1 -->

# Acceptance Review — Image-Backed Annotation Container (#465)

**Design/plan:** [design](../../design/issue-465-image-annotation-container-design-2026-09-27.md),
[design amendment](../../design/issue-465-image-annotation-container-design-amendment-2026-09-27.md),
[architecture review](issue-465-image-annotation-container-architecture-review-2026-09-27.md)
and its [amendment](issue-465-image-annotation-container-architecture-review-amendment-2026-09-27.md),
[implementation plan](../../planning/active/issue-465-image-annotation-container-implementation-plan-2026-09-27.md)
and its [amendment](../../planning/active/issue-465-image-annotation-container-implementation-plan-amendment-2026-09-27.md).
**Base:** `origin/main` at `3aa616c3` (rebased before implementation; contains
#488). **Commits:** `908c6ca3` (Theme token, closure fix, Layout nine-slice
geometry), `9bd5bb10` (Scene `ScenePaint.image`, adapters), `267232bd`
(closure read-ledger fix, Scene delivery ownership, contrast/perceptibility
unit proofs), `733d7f83` (evidence corpus counts). **CI:** pending (the lead
fills in the run link after push).

## Literal issue acceptance

### Issue #465

- Source: [Issue #465](https://github.com/tya5/chrona/issues/465)
- Observed: 2026-09-27

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | A Theme can bind an image to the annotation container, with stretch insets and a content inset. A View cannot. | met | `schemas/theme-v0.11.schema.yaml`'s additive `outline: image` branch (`image`, `sliceInsetsEm`, `contentInsetEm`); [`theme_tokens.py`](../../../src/chrona/presentation/model/theme_tokens.py)'s `AnnotationContainerToken`; [`test_theme_tokens.py`](../../../tests/unit/chrona/presentation/model/test_theme_tokens.py) round-trip and rejection tests. No View schema (v0.25) field was added; [`test_image_annotation_container.py`](../../../tests/integration/test_image_annotation_container.py)`::test_a_theme_only_binding_resolves_an_icon_catalog_entry_no_view_selected` proves a Theme-only binding places and paints a note whose View never names the artwork. | — |
| 2 | Layout measures and wraps note text inside the content inset, and the image is stretched to the resulting box. | met | `surface_composer.py`'s content-box/paint-box split (paint box = content box + `contentInsetEm`, used by candidate search/collision); [`image_slice_geometry.py`](../../../src/chrona/presentation/layout/image_slice_geometry.py) computes the nine-slice tiles from that paint box; [`test_image_slice_geometry.py`](../../../tests/unit/chrona/presentation/layout/test_image_slice_geometry.py) (degenerate insets, box-smaller-than-border clamping); `test_image_annotation_container.py::test_the_note_text_is_measured_inside_the_content_inset_not_the_mounting` asserts the rendered text sits strictly inside the paint box, not at its edge. | — |
| 3 | Contrast and perceptibility checks treat the image's content area as the ground for the note text. | met | The container stays an ordinary `Rect`/`Symbol` primitive; its Theme-declared `fill` (the artwork's own content-area colour, e.g. `surfaceRaised` `#16213A` in the committed evidence) is unchanged and still paints. `contrast_policy.py`'s `_ground_under` and `perceptibility.py`'s `_occlusion_findings`/`_paint_findings` need zero code changes, proven directly by [`test_contrast_policy.py::test_an_image_backed_container_grounds_note_text_by_its_declared_fill_465`](../../../tests/unit/chrona/presentation/scene/test_contrast_policy.py) and [`test_perceptibility.py::test_an_image_backed_rects_paint_image_does_not_change_occlusion_465`](../../../tests/unit/chrona/presentation/scene/test_perceptibility.py). `tools/check_scene_perceptibility.py` passes on the full corpus including the new slide (26 scenes, 0 errors). **Caveat, not a #465 gap:** `annotation-note-text`/`annotation-note-box` (the #466 candidate-mechanism roles) are not yet in `semantic_registry.py`'s classified contrast set at all — a pre-existing #466 condition, unchanged by an image outline versus a rectangle or balloon one. This means `tools/presentation_contrast.py`'s numeric floor-check does not yet evaluate note text for *any* container kind. See "Programme-level criteria" below. | — |
| 4 | One committed slide renders HALCYON-1 `02-programme-board` with image-backed notes, and its SVG and PNG evidence is reproducible. | met | New slide [`15-gallery-image-notes.svg`](../../../examples/halcyon-1/generated/15-gallery-image-notes.svg) and [`15-gallery-image-notes.scene.json`](../../../examples/halcyon-1/generated/15-gallery-image-notes.scene.json) (manifest entry `gallery-image-notes` in [`manifest.yaml`](../../../examples/halcyon-1/manifest.yaml)), derived from `02-programme-board` (same Project, same base View content, three of the same Project notes: `window`, `tvac`, `station`; see [`views/15-gallery-image-notes.yaml`](../../../examples/halcyon-1/views/15-gallery-image-notes.yaml)) without editing `02-programme-board.yaml`/`themes/wallboard.yaml`/`views/02-programme-board.yaml`. `tools.regenerate_public_examples --write` then `--check` both report 26 slides with no other slide's bytes changed. | — |
| 5 | A Theme without the binding renders exactly as today. | met | [`theme_tokens.py`](../../../src/chrona/presentation/model/theme_tokens.py)'s `annotation_container` returns `None`/unchanged shapes for a role without the token ([`test_theme_tokens.py::test_annotation_container_is_none_without_the_binding`](../../../tests/unit/chrona/presentation/model/test_theme_tokens.py)); `surface_composer.py`'s content/paint-box split defaults every content inset to `0.0` unless `outline == "image"`; `tools.regenerate_public_examples --check` (26 slides) reports no byte change to any of the 25 pre-existing slides, including `test_candidate_placement.py`'s existing balloon fixture. | — |

## Programme-level criteria (optional)

- **#466 contrast-classification gap (named, not fixed here).** `annotationNoteBox`/`annotationNoteText` have no `ContrastClass` in `semantic_registry.py`. Classifying them would require every existing Theme that already uses the #466 candidate mechanism (at least `examples/controller-z/themes/executive-light.yaml`, exercised by `tests/integration/test_candidate_placement.py`) to also declare `roles.annotation-note-text.contrastTreatment`, per `theme_tokens.contrast_treatment`'s existing requirement for any STATE_TEXT-classified role. That is a cross-cutting change to #466's own shipped Themes, outside this issue's boundary ("another dev session owns #466... do not change their design"). Recommend a small follow-up issue, owned by whoever owns #466/#459 next, to classify these roles once its Theme-migration cost is accepted.
- **Tenth Frame's shared container and Marquee's rotation** remain out of scope, named in the design plan, not silently absorbed.
- **Generalized third-party artwork import** (a `chrona container-image-catalog import`-style command) is not built; the one committed asset (`examples/halcyon-1/assets/annotation-container.png`, generated by `tools/generate_container_image_placeholder.py`) is repository-owned, non-photographic, and hand-normalized into an ordinary `chrona/icon-catalog/v0.3` raster entry.

## Architecture conclusion

- **View:** unchanged (no schema bump); a View cannot bind or override the container image, by construction (no View field reads `annotationContainer`).
- **Theme:** Theme v0.11 extended in place, additive-only (`outline: image`), no version bump, matching repository precedent (`progressInset` #430, `chipPadding` #428).
- **Layout:** the content-box/paint-box split and nine-slice tile geometry are pure additions; candidate search, obstacle registration, and #466's fallback/warning contract are untouched for `rectangle`/`balloon` roles.
- **Scene:** the container is exactly the `Rect`/`Symbol` primitive it was before #465; `ScenePaint.image` is additive, parallel to the existing `gradient` fill mode. Contrast and perceptibility policy modules are byte-unchanged.
- **Adapters:** SVG paints each completed tile as one nested clipping `<svg>`/`<image>` pair, reusing the existing raster-icon base64 embedding; PNG stays derived from SVG via resvg. No adapter computes a tile boundary or stretch ratio.
- **Closure:** one real gap was found and fixed during implementation — `RenderClosure.icon_assets` was selected only from a View's `visuals`, which would have made a Theme-only container-image reference always fail even inside a correctly pinned Context. `_theme_container_image_references` (both the immutable-Context and Draft resolution paths) closes this without widening what a View can select.
- **Release gates:** focused tests (`tests/unit/chrona/presentation`, `tests/integration`, `tests/cli`, `tests/acceptance`): 1105 passed, 24 skipped, 0 failed. `conformance/run_conformance.py`: PASS (all checks, including `scene-primitive-delivery`, `semantic-realization-coverage`, `presentation-coverage`, `diagnostic-inventory`, `declared-value-inventory`, all refreshed for this change). `tools.regenerate_public_examples --write` then `--check`: 26 slides, reproducible, only the one new slide's bytes are new.

This review supports closing #465 pending the lead's disposition on the
named #466 contrast-classification gap (a follow-up, not a blocker to this
issue's own literal rows) and CI.
