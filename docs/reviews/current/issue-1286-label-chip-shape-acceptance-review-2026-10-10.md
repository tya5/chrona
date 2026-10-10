<!-- chrona:literal-acceptance/v1 -->

# Issue #1286 — label chip shape acceptance

Validation checkpoint: `1d99c5d2620efbf63d0b949a527fd2db221cdcca`, ordinarily
adopting ready main `612c1449d68e4abf2267f1bad7db10360cbf7b05`, including
merged #1287, #1336, #1279 and dev B's legend fix. The exact base's
[derived-main gate](https://github.com/tya5/chrona/actions/runs/38046325711) succeeded.
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

Combined chip/point/legend/viewport/host integration batch: 190 passed (103.75s).
Supplementary filled-contour, label-intent, diagnostic-provenance, presentation
closure, graphics-schema and viewport tests: 98 passed (29.60s).
The added frozen absent-token regression and existing rectangle comparison
both passed (4.43s): 289 unique focused tests in total.
Independent unchanged-input replay against public pre-feature parent `127392c4`
matches raw Scene 22,949 bytes, SHA256 `e5f8b0c395e6b891d065e9152f2aa302d51d4f5162e3680edec12d802f2b93ea`,
and SVG 6,992 bytes, SHA256 `74bf8d570ca05067f0000a3002520bb237113b11ac682e21ae367ec0e82c3e0b`.
`test_absent_shape_preserves_frozen_pre_feature_scene_and_svg_bytes` retains
both lengths and hashes without geometry or provenance normalization.

Final-base S0 (`python -m tools.schema_equivalence --base-rev origin/main`)
against exact ready `612c1449` passed: L1 37 equal / one Theme expansion
(three declared pointers); L2 482 tracked / 378 mapped / four unchanged invalid
documents / zero unparseable; L3 739 probes (462 reject / 277 accept).
L2+L3 took 36.6s within the 60s budget. Baseline absence notes and inherited
five Layout L2 allowances are disclosed; the latter have zero later schema
merges and are nonblocking. No pruning or timing waiver was used.
Only three pending chipShape L1 allowances remain; the unrelated landed
group-header L1 allowance was already retired by public commit `b982d583`.
No authored examples, workflows or generated outputs differ from the ready base.

## Architecture conclusion

Layout owns one immutable completed shape, text-safe rectangle and once-expanded visible footprint, reused by lane demand, early as-of reserve and final placement. Scene projects canonical parent/part IDs and resolves paint; adapters serialize completed paths. Catalog coverage uses exact filled-path boolean difference, not bounding boxes or samples. Independent review found and verified correction of a numeric-spacing mismatch. Legacy rectangular geometry remains unchanged; catalog parts and declared text-follows-box remain intact.

Independent integration review verified that chip coverage retains the merged
point-outline contour decoder and that measured-chip transport retains declared
viewport warnings, small caps, completed collision bounds and slot headings.

Release remains pending: fresh exact-head PR checks, public before/after artifact inspection, automatic derived sync and successful three-OS pytest/conformance/wheel on the exact main containing the final review.
