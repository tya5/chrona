<!-- chrona:literal-acceptance/v1 -->

# Issue #1286 — label chip shape acceptance

Validation checkpoint: `8799fc137edc1db5f87ed0f1b9a7f22bdaa455a8`, ordinarily
adopting published #1287 head `88729d8e76d34b12ff4144441e29e79f5bf5d9bb`
and ready main `127392c426010f8381c984d8ff45f6c1e46f3791`, including the
shared contour correction and dev B's legend fix. #1287 is not yet merged.
No chip PR is open.
[Current design, architecture review and plan](https://github.com/tya5/chrona/issues/1286#issuecomment-6088639263).
Local acceptance only: no PR, public artifact or exact-main release gate is complete. Do not close.

## Literal issue acceptance

### Issue #1286

- Source: [Issue #1286](https://github.com/tya5/chrona/issues/1286)
- Observed: 2026-10-10

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | A chip with `burst` is a closed polygon `Symbol` whose vertex count equals `2 * points` and whose inner radius equals `innerRatio` times the outer radius. | met | [Geometry tests](../../../tests/unit/chrona/presentation/layout/test_chip_shape_geometry.py) exercise odd/even N, concave/convex cases and extreme ratios. [Rendered tests](../../../tests/integration/test_label_chip_shapes.py) verify closed Scene vertices and matching actual SVG coordinates. | — |
| 2 | The text bounds lie fully inside the polygon's inscribed region; the chip does not collide with marks or labels under the existing as-of placement. | met | [Rendered as-of tests](../../../tests/integration/test_label_chip_shapes.py) compare all text corners with the actual SVG polygon's inscribed disk, check mark/text non-overlap, and prove content-dependent pre-row reserve, including tabular digits. [All-role tests](../../../tests/integration/test_period_variance_chip_shapes.py) verify period/variance Scene and SVG projection. | — |
| 3 | Contrast gate judges the text over the chip fill. Absent token is byte-identical. Synthetic fixture test. | met | [Ground tests](../../../tests/unit/chrona/presentation/scene/test_chip_symbol_ground.py) exercise actual paths, holes, ordered translucent parts and unreadable geometry. [Synthetic render tests](../../../tests/integration/test_label_chip_shapes.py) prove that text-colored chip fill fails the actual as-of contrast gate while a readable control renders, and verify explicit rectangle visual identity. Independent unchanged-input replay against the public parent compares complete raw Scene and SVG bytes without provenance normalization; hashes below. | — |
| 4 | Do not edit `examples/**`; the reviewer adopts it in slide 25. | met | [Scope/ownership](https://github.com/tya5/chrona/issues/1286#issuecomment-6088639263): no authored examples or generated corpus edits; adoption is reviewer-owned under board #454. | — |

## Programme-level criteria (optional)

Synthetic render evidence: 12 cases across both integration files; the final as-of file passed 8 tests and the period/variance file passed 4. Final focused closure/measurement/lane/ground/period batch: 43 passed; builder/geometry/lane/ground batch: 88 passed; legacy chip/as-of/viewer-fit batch: 48 passed. Independent absent-token replay: Scene 22,949 bytes, SHA256 `e5f8b0c395e6b891d065e9152f2aa302d51d4f5162e3680edec12d802f2b93ea`; SVG 6,992 bytes, SHA256 `74bf8d570ca05067f0000a3002520bb237113b11ac682e21ae367ec0e82c3e0b`; root verified both complete streams with `cmp`.

Current adopted-parent batch: 40 passed (12.08s) for chip, contour, hosted-note,
legend and host-identity tests; remaining period/variance and schema tests:
9 passed (3.76s). Full S0 against exact ready `127392c4` passes: L1 37 equal,
one declared Theme expansion; L2 470 tracked/367 mapped/4 unchanged invalid
documents; L3 739 probes (462 reject/277 accept). L2+L3: 32.5s within 60s.
The inherited landed group-header allowance remains unchanged and nonblocking.
Final-base S0, CI and artifact evidence remain required after #1287 merges.

## Architecture conclusion

Layout owns one immutable completed shape, text-safe rectangle and once-expanded visible footprint, reused by lane demand, early as-of reserve and final placement. Scene projects canonical parent/part IDs and resolves paint; adapters serialize completed paths. Catalog coverage uses exact filled-path boolean difference, not bounding boxes or samples. Independent review found and verified correction of a numeric-spacing mismatch. Legacy rectangular geometry remains unchanged; catalog parts and declared text-follows-box remain intact.

Release remains pending: #1287 ready-main adoption, fresh exact-head PR checks, public before/after artifact inspection, automatic derived sync and successful three-OS pytest/conformance/wheel on the exact main containing the final review.
