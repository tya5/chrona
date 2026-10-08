<!-- chrona:literal-acceptance/v1 -->

# Issue #888 — glyph frame acceptance

Part1 local acceptance; publication and release gates pending. Part2 remains open.
Implementation: `fd8821df436df39814bf766410d353f6a1fb9520`, on ready main
`c36c43de0de6cfc6b280c9d55296a0f8c2e14d79`.
Source: [#888](https://github.com/tya5/chrona/issues/888), observed 2026-10-08.
Current plan: [living Status](https://github.com/tya5/chrona/issues/888#issuecomment-6048944931).

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | The frame role is declared, completed by Layout and covered by synthetic tests: run count and spacing, corners, a length that does not divide evenly, default output unchanged without the role. | met | `test_frame_glyph.py`, `test_surface_frame_glyph_completion.py`, `test_frame_glyph_theme_schema.py` and `test_frame_glyph_render.py`: typed closure, residual spacing, parent ordering and real-adapter absent-role byte identity. | — |
| 2 | Treatments beyond the baseline profile follow #478 where they need one. | met | `test_frame_glyph_admission.py` and real rendering: required exact-pointer failure, optional whole-border omission with panel/content preserved, rich SVG/PNG. | — |
| 3 | Evidence: the Marquee title through YAML, rendered through SVG and PNG and read. | met | Authored `tests/fixtures/surface-decoration/marquee-glyph-frame.yaml` plus integration rendering. Root inspected SVG raster and native PNG: readable light title, four-corner bulb border, unchanged content. | — |
| 4 | Each of the three is declared and covered by synthetic tests including determinism (two renders equal, a different seed differs), default output unchanged without them. | deferred | Ink-only/overlay/seeded textures are Part2, not implemented by this PR. | #888 Part2, living Status above |
| 5 | The gates treat an overlay as ground over what it covers. | deferred | Frame ink is tested; this does not prove above-content texture overlay compositing. | #888 Part2, living Status above |
| 6 | Evidence: Montmartre and Off-World surfaces through YAML, rendered through SVG and PNG and read. | deferred | Not produced by Part1. | #888 Part2, living Status above |

Verification: focused frame/schema/paint/contrast/artwork regression group **236 PASS**;
latest `.venv/bin/python -m pytest -q tests/integration/test_frame_glyph_render.py tests/unit/chrona/presentation/model/test_frame_glyph_role_consumers.py`: **13 PASS**.
`.venv/bin/python -m tools.schema_equivalence --base-rev origin/main`: PASS, additive optional properties;
`.venv/bin/python tools/check_layout_float_accumulation.py` and `git diff --check`: PASS.

Layout owns all glyph paths/run geometry; Scene projects one admitted batch and resolves used paint channels.
Sparse ink/contact remains renderer-neutral; ordered ground composition preserves opaque/translucent host,
cone and annotation boundaries. No `examples/**` or generated evidence was authored.
CI shared snapshot/count table and the exact published three-OS release run remain required;
no zero-diff claim or issue closure is authorized by these local results.
