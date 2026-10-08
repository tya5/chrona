<!-- chrona:literal-acceptance/v1 -->

# Issue #888 — surface decoration acceptance

Part1 merged in [PR #1223](https://github.com/tya5/chrona/pull/1223), commit
`497b2bdc51f04001c9d177b8becd03f45b9bd918`. Part2 local acceptance on public
WIP `e1d680534cfc59a24131f6ee7fb90bf83b3ed217`, based on ready main
`ce6abfa4f3fa7aab1dacd8e244c09226947d3860`; final implementation and this review
are published together in [PR #1225](https://github.com/tya5/chrona/pull/1225).
Final-head checks and exact-main three-OS release remain pending; the issue stays
open until they pass.
Current plan: [living Status](https://github.com/tya5/chrona/issues/888#issuecomment-6048944931).

## Literal issue acceptance

### Issue #888

- Source: [#888](https://github.com/tya5/chrona/issues/888)
- Observed: 2026-10-08

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | The frame role is declared, completed by Layout and covered by synthetic tests: run count and spacing, corners, a length that does not divide evenly, default output unchanged without the role. | met | [Geometry](../../../tests/unit/chrona/presentation/layout/test_frame_glyph.py), [composition](../../../tests/unit/chrona/presentation/layout/test_surface_frame_glyph_completion.py), [schema](../../../tests/unit/chrona/presentation/contracts/test_frame_glyph_theme_schema.py) and [real rendering](../../../tests/integration/test_frame_glyph_render.py): closure, residual spacing, parent ordering and absent-role bytes. | — |
| 2 | Treatments beyond the baseline profile follow #478 where they need one. | met | [Frame admission](../../../tests/unit/chrona/presentation/scene/test_frame_glyph_admission.py), [surface admission](../../../tests/unit/chrona/presentation/scene/test_surface_overlays.py) and [radial paint](../../../tests/unit/chrona/presentation/scene/test_canvas_overlay_paint.py): required exact-pointer failure, optional whole-treatment omission, rich SVG/PNG. | — |
| 3 | Evidence: the Marquee title through YAML, rendered through SVG and PNG and read. | met | Authored [YAML](../../../tests/fixtures/surface-decoration/marquee-glyph-frame.yaml) and [integration](../../../tests/integration/test_frame_glyph_render.py). Root inspected SVG raster and native PNG: readable light title, four-corner bulb border, unchanged content. | — |
| 4 | Each of the three is declared and covered by synthetic tests including determinism (two renders equal, a different seed differs), default output unchanged without them. | met | [Declarations](../../../tests/unit/chrona/presentation/model/test_theme_canvas_overlays.py), [seeded geometry](../../../tests/unit/chrona/presentation/layout/test_seeded_pattern.py), [completion](../../../tests/unit/chrona/presentation/layout/test_surface_canvas_overlays.py), [projection](../../../tests/unit/chrona/presentation/scene/test_surface_overlays.py), and [real adapters](../../../tests/integration/test_surface_texture_render.py): repeated bytes equal, changed seed differs, genuine absent-role resource differential. | — |
| 5 | The gates treat an overlay as ground over what it covers. | met | [Both quality gates](../../../tests/unit/chrona/presentation/scene/test_surface_treatment_quality.py), [ordered pairs](../../../tests/unit/chrona/presentation/scene/test_surface_overprint.py) and [periodic ink contact](../../../tests/unit/chrona/presentation/scene/test_pattern_ink.py): foreground/backdrop correlation, opaque erasure, holes, prior hosts, gradient sampling, caps/joins and fail-closed bounded contact. | — |
| 6 | Evidence: Montmartre and Off-World surfaces through YAML, rendered through SVG and PNG and read. | met | Authored [Montmartre](../../../tests/fixtures/surface-decoration/montmartre-surface-textures.yaml), [Off-World](../../../tests/fixtures/surface-decoration/offworld-surface-textures.yaml), [scanline catalogue import](../../../tests/fixtures/surface-decoration/scanlines-theme-assets.yaml), and [integration](../../../tests/integration/test_surface_texture_render.py). Root inspected both SVG rasters and native PNGs: readable content; grain/vignette and rain/scanlines visible; horizon gradient preserved through rain holes. Off-World headings use fixture-only Scheme bindings. | — |

## Programme-level criteria (optional)

[PR #1223 shared snapshot](https://github.com/tya5/chrona/actions/runs/37725212704):
all 67 public Scene/SVG pairs byte-identical; only diagnostic inventory source locations and two new ingress sites change.

[Part2 snapshot at95ce116c](https://github.com/tya5/chrona/actions/runs/37729757646),
artifact11529825209: all67 Scene/SVG pairs byte-identical, no added/retired outputs
or runtime diagnostic changes. Only declared-value source locations, diagnostic
sites/source locations and newly declared presentation vocabulary reports differ.
The final corrected head must repeat shared-snapshot verification before merge.

## Architecture conclusion

Part1 focused frame/schema/paint/contrast/artwork group: **236 PASS**; adapter/consumer
tests: **13 PASS**; PR CI passed. Part2 batched geometry/quality and actual SVG/PNG
integration: **218 PASS**, with a later extreme-coordinate contact regression passing
in the focused quality group. Full schema-equivalence passes with precise optional-field
L1 declarations. Schema annotations and semantic-registry production reachability
are corrected and checked. The initial CI conformance failure is only the
diagnostic actionability ratchet (three new bare error sites); owner-local detail
and assertions correct them without changing policy counts. Diagnostic/model/SVG
regressions: **35 PASS**. No generated report was patched to absorb the changes.

Layout owns all glyph paths/run geometry; Scene projects one admitted batch and resolves used paint channels.
Sparse ink/contact remains renderer-neutral; ordered ground composition preserves opaque/translucent host,
cone and annotation boundaries. Layout also completes seeded tiles and radial geometry;
Scene projects fixed after-content layers, and both quality gates observe ordered
overprinted pairs. SVG serializes completed geometry and PNG uses that same SVG.
No `examples/**`, bundled bitmap, or generated public evidence was authored.
CI shared snapshot/count table and the exact published three-OS release run remain required;
no zero-diff claim or issue closure is authorized by these local results.
