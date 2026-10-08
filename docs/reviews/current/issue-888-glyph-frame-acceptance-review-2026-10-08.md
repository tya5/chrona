<!-- chrona:literal-acceptance/v1 -->

# Issue #888 — glyph frame acceptance

Part1 local acceptance; publication and release gates pending. Part2 remains open.
Implementation: `fd8821df436df39814bf766410d353f6a1fb9520`, on ready main
`c36c43de0de6cfc6b280c9d55296a0f8c2e14d79`.
Current plan: [living Status](https://github.com/tya5/chrona/issues/888#issuecomment-6048944931).

## Literal issue acceptance

### Issue #888

- Source: [#888](https://github.com/tya5/chrona/issues/888)
- Observed: 2026-10-08

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | The frame role is declared, completed by Layout and covered by synthetic tests: run count and spacing, corners, a length that does not divide evenly, default output unchanged without the role. | met | [Geometry](../../../tests/unit/chrona/presentation/layout/test_frame_glyph.py), [composition](../../../tests/unit/chrona/presentation/layout/test_surface_frame_glyph_completion.py), [schema](../../../tests/unit/chrona/presentation/contracts/test_frame_glyph_theme_schema.py) and [real rendering](../../../tests/integration/test_frame_glyph_render.py): closure, residual spacing, parent ordering and absent-role bytes. | — |
| 2 | Treatments beyond the baseline profile follow #478 where they need one. | met | [Admission](../../../tests/unit/chrona/presentation/scene/test_frame_glyph_admission.py) and [rendering](../../../tests/integration/test_frame_glyph_render.py): required exact-pointer failure, optional whole-border omission with panel/content preserved, rich SVG/PNG. | — |
| 3 | Evidence: the Marquee title through YAML, rendered through SVG and PNG and read. | met | Authored [YAML](../../../tests/fixtures/surface-decoration/marquee-glyph-frame.yaml) and [integration](../../../tests/integration/test_frame_glyph_render.py). Root inspected SVG raster and native PNG: readable light title, four-corner bulb border, unchanged content. | — |
| 4 | Each of the three is declared and covered by synthetic tests including determinism (two renders equal, a different seed differs), default output unchanged without them. | deferred | [Part2 plan](https://github.com/tya5/chrona/issues/888#issuecomment-6048944931): ink-only/overlay/seeded textures not implemented by Part1. | [#888 Part2](https://github.com/tya5/chrona/issues/888#issuecomment-6048944931) |
| 5 | The gates treat an overlay as ground over what it covers. | deferred | [Frame ink tests](../../../tests/unit/chrona/presentation/scene/test_frame_glyph_ground.py) do not prove above-content texture overlay compositing. | [#888 Part2](https://github.com/tya5/chrona/issues/888#issuecomment-6048944931) |
| 6 | Evidence: Montmartre and Off-World surfaces through YAML, rendered through SVG and PNG and read. | deferred | [Part2 plan](https://github.com/tya5/chrona/issues/888#issuecomment-6048944931): not produced by Part1. | [#888 Part2](https://github.com/tya5/chrona/issues/888#issuecomment-6048944931) |

## Programme-level criteria (optional)

[PR #1223 shared snapshot](https://github.com/tya5/chrona/actions/runs/37723520373):
all 67 public Scene/SVG pairs byte-identical; only diagnostic inventory source locations and two new ingress sites change.

## Architecture conclusion

Verification: focused frame/schema/paint/contrast/artwork regression group **236 PASS**;
latest `.venv/bin/python -m pytest -q tests/integration/test_frame_glyph_render.py tests/unit/chrona/presentation/model/test_frame_glyph_role_consumers.py`: **13 PASS**.
`.venv/bin/python -m tools.schema_equivalence --base-rev origin/main`: PASS, additive optional properties;
`.venv/bin/python tools/check_layout_float_accumulation.py` and `git diff --check`: PASS.

Layout owns all glyph paths/run geometry; Scene projects one admitted batch and resolves used paint channels.
Sparse ink/contact remains renderer-neutral; ordered ground composition preserves opaque/translucent host,
cone and annotation boundaries. No `examples/**` or generated evidence was authored.
CI shared snapshot/count table and the exact published three-OS release run remain required;
no zero-diff claim or issue closure is authorized by these local results.
