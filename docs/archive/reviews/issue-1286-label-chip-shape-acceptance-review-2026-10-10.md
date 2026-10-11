<!-- chrona:literal-acceptance/v1 -->

# Issue #1286 — label chip shape acceptance

Released by [PR #1348](https://github.com/tya5/chrona/pull/1348) on exact main
`ddbf4cebfa34cf558edc38746222a7a8b4a41332`, containing the literal review.
[Release 38051468291](https://github.com/tya5/chrona/actions/runs/38051468291)
completed successfully: Ubuntu/macOS/Windows full pytest, conformance, exact-SHA
checkout, OS probe, wheel smoke and finalizer; newest-Python materializers and MCP floor.
[Closing verification and current design](https://github.com/tya5/chrona/issues/1286#issuecomment-6088639263).

## Literal issue acceptance

### Issue #1286

- Source: [Issue #1286](https://github.com/tya5/chrona/issues/1286)
- Observed: 2026-10-10

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | A chip with `burst` is a closed polygon `Symbol` whose vertex count equals `2 * points` and whose inner radius equals `innerRatio` times the outer radius. | met | [Geometry](../../../tests/unit/chrona/presentation/layout/test_chip_shape_geometry.py) and [real Scene/SVG](../../../tests/integration/test_label_chip_shapes.py) test odd/even counts, extreme ratios, closed vertices and coordinates. | — |
| 2 | The text bounds lie fully inside the polygon's inscribed region; the chip does not collide with marks or labels under the existing as-of placement. | met | [As-of render](../../../tests/integration/test_label_chip_shapes.py) checks actual polygon containment, mark/text non-overlap and pre-row reserve; [period/variance](../../../tests/integration/test_period_variance_chip_shapes.py) verifies the shared projection. | — |
| 3 | Contrast gate judges the text over the chip fill. Absent token is byte-identical. Synthetic fixture test. | met | [Paint grounds](../../../tests/unit/chrona/presentation/scene/test_chip_symbol_ground.py) and [synthetic render](../../../tests/integration/test_label_chip_shapes.py) exercise actual fill contrast and frozen absent-token complete raw Scene/SVG bytes, without normalization. [Artifact/byte receipt](https://github.com/tya5/chrona/issues/1286#issuecomment-6096882778). | — |
| 4 | Do not edit `examples/**`; the reviewer adopts it in slide 25. | met | [Scope and closure audit](https://github.com/tya5/chrona/issues/1286#issuecomment-6088639263): no authored example edits; reviewer adoption is not a dev closing condition. | — |

## Programme-level criteria (optional)

Layout owns immutable completed shape/text-safe geometry and once-expanded
obstacles, shared by demand, lanes and final placement. Scene projects closed
Symbol/Text and actual paint grounds; adapters serialize. Exact filled-path
coverage, not sampling or bounding-box approximation, checks catalog text safety.
Combined installed-font/chip integration passed; no ownership defect remains.
All 46 corpus Scene/SVG pairs were raw-byte identical; only three expected reports changed.
Initial 289 unique focused cases and later 44 chip/schema, six CLI and 96 combined
cases passed. A golden enum omission was corrected. Local S0's sole timing failure
(102.8/60s on a loaded host) was not waived: unchanged CI S0 passed 12.9/60s.
The required exact-main full release above passed before deliberate issue closure.
