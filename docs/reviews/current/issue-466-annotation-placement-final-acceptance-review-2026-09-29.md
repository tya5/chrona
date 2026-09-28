<!-- chrona:literal-acceptance/v1 -->

# #466 final acceptance: annotation placement

**Public base:** `2dd699236d2d631cc1fb08bad8cd55aaf1bb45ae` ([C4 PR #522](https://github.com/tya5/chrona/pull/522)); C3 was merged by [PR #521](https://github.com/tya5/chrona/pull/521). **Release gate:** [CI 36459884806](https://github.com/tya5/chrona/actions/runs/36459884806) passed Ubuntu, macOS, and Windows conformance, full pytest, and wheel/smoke, plus newest-Python public materializer reproduction. **Design:** [C3 review](issue-466-c3-balloon-scene-kind-architecture-review-2026-09-29.md), [C4 review](issue-466-c4-contrast-closure-architecture-review-2026-09-27.md), and the [C4 disposition correction](issue-466-c4-decoration-disposition-architecture-review-2026-09-29.md).

C4 focused tests: 159 passed. Local conformance, 29-slide public materializer `--check`, Scene perceptibility (29 scenes, zero errors), presentation contrast `--check`, and generated inventory/coverage/font-identity checks passed. The report contains 13 `annotation-note-box` primitives (minimum 1.435:1 versus 1.10:1) and 13 `annotation-note-text` primitives (minimum 13.973:1 versus 4.50:1), across five slides. Fifteen Scene files changed only by Theme identity and required note-text contrast metadata; no SVG or PNG bytes changed. Actual 02, 15 and Controller-Z annotation SVGs were rasterized and inspected together: 02 retains three legible notes and routed tails without an as-of crossing; 15's image-backed note text remains legible over the declared flat representative fill; Controller-Z notes remain visible. The SVG SHA-256 values are respectively `705d60653ca2100dd74176d9fdac9fd4846b90b0f958874e2d4e823f6b65d00d`, `2b667bf455d3430cb62a4e7cfe05bdfd6377951bd7eb973fdd26c7225831f363`, and `527db2779afbc57d1827414b0226695d8c191474f070883c4d783763b0dcce26`.

## Literal issue acceptance

### Issue #466

- Source: [Issue #466](https://github.com/tya5/chrona/issues/466)
- Observed: 2026-09-29

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | One obstacle set is computed per surface and used by every placement and leader route. A committed test shows a note beside a dependency line no longer covers it. | met | [O2 acceptance review](issue-466-shared-obstacle-prerequisite-acceptance-review-2026-09-26.md); [C3 review](issue-466-c3-routed-tail-implementation-review-2026-09-29.md). | — |
| 2 | Placement candidates are declared as region, search, obstacles and connector. The existing rung names expand to candidates, and all committed evidence is unchanged by that refactor. | met | [C1/C2 review](issue-466-candidate-normalization-implementation-review-2026-09-26.md); [Spec 33](../../specification/33-intent-oriented-layout.md). | — |
| 3 | A nearest-free search exists. With candidates plot → nearest-free → tail and no rail slot, HALCYON-1 `02-programme-board` places all three notes without covering a mark, a label or a dependency path, and without crossing the as-of line. | met | [02 View](../../../examples/halcyon-1/views/02-programme-board.yaml), [02 SVG](../../../examples/halcyon-1/generated/02-programme-board.svg), [C3 geometry review](issue-466-c3-routed-tail-implementation-review-2026-09-29.md); inspected rendered output. | — |
| 4 | The same slide with candidates plot → nearest-free first, then rail, falls back to the rail when the plot is made too crowded, with a diagnostic naming the candidate used. | met | [Crowded-clone integration test](../../../tests/integration/test_issue_466_c3_fallback.py) and [C3 review](issue-466-c3-routed-tail-implementation-review-2026-09-29.md). | — |
| 5 | Placement is deterministic and bounded. The placement decision records the candidate chosen and the search count. | met | [C3 decision tests and review](issue-466-c3-routed-tail-implementation-review-2026-09-29.md), [bounded search tests](../../../tests/unit/chrona/presentation/layout/test_annotation_search.py). | — |
| 6 | A Theme can draw the tail and balloon outline. A Theme without it renders as today. | met | [Wallboard Theme](../../../examples/halcyon-1/themes/wallboard.yaml), [02 SVG](../../../examples/halcyon-1/generated/02-programme-board.svg), [C3 review](issue-466-c3-routed-tail-implementation-review-2026-09-29.md); C4 confirms Theme/Scene contrast closure without SVG byte changes. | — |
| 7 | The specification describes the model once, and no longer as a list of per-rung behaviours; `06-view-model.md` and `44-usable-explicit-rows-and-annotation-rail.md` point at it. | met | [Spec 33](../../specification/33-intent-oriented-layout.md), [Spec 06](../../specification/06-view-model.md), [Spec 44](../../specification/44-usable-explicit-rows-and-annotation-rail.md); [C3 review](issue-466-c3-routed-tail-implementation-review-2026-09-29.md). | — |

## Programme-level criteria (optional)

C4 additionally closes the note-role contrast and same-source opaque-ground contract required by its published design: [Spec 07](../../specification/07-style-and-theme.md), [Spec 08](../../specification/08-scene-and-rendering.md), [contrast report](../../diagnostics/presentation-contrast.md), and the green release gate above. No #466 acceptance item remains deferred.

## Architecture conclusion

Layout owns the shared obstacle set, candidate search, completed note geometry and tail route. Theme supplies the finite note paint and required text treatment; Scene projects completed primitives and checks their same-source representative ground; adapters serialize without placement or contrast repair. The C4 correction keeps contrast classification separate from background-treatment admission, preserving this boundary. #466 is accepted for closure on the verified public base.
