<!-- chrona:literal-acceptance/v1 -->

# Issue #1287 — point glyph outline acceptance

Current adoption: ready main `4f4ee94ccc21c8d3c85021a1dc50a931d068e044`,
including #1283, #1327, dev B's #1219/#1273/#1214 and the reviewer's roadmap.
[Derived gate](https://github.com/tya5/chrona/actions/runs/38027686440) succeeded.
Integration after source adoption `73405aa1`: 77 focused tests pass (41.72s)
and both technical-print regressions pass (2.86s). Bot adoption `9e35aaf5`
changes no product/test bytes. Previous head `b55e10ed`
[CI](https://github.com/tya5/chrona/actions/runs/38026333704) passes every
substantive check; only exact-base readiness fails after main advances.
Fresh 46-slide snapshot, current exact-head checks and containing-main release
remain required; predecessor audits are not current-base acceptance.
[Selected design and architecture review](https://github.com/tya5/chrona/issues/1287#issuecomment-6088427990).
Earlier [PR CI](https://github.com/tya5/chrona/actions/runs/38022653852) exposed a
closed-quadratic implicit-start decoding bug and a corpus-dependent hosted-note test.
The shared decoder preserves exact curves/holes; independent review found no defect.
[Synthetic full-pipeline identity tests](../../../tests/integration/test_hosted_note_index_identity.py)
replace the dense-corpus identity fixture without relaxing host existence, exact
single/multipart identity or paint-order assertions, and check actual SVG IDs.
Do not close.

## Literal issue acceptance

### Issue #1287

- Source: [Issue #1287](https://github.com/tya5/chrona/issues/1287)
- Observed: 2026-10-10

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | With `stroke` and `strokeWidth` bound, the completed gate `Symbol` carries a stroke paint of that width on its filled contour, and the legend swatch for the same role carries the identical paint. | met | [Scene/SVG integration tests](../../../tests/integration/test_point_glyph_role_outline.py): inline/catalogue × lane/automatic point and legend share paint; inside/center/outside clips; catalogue intrinsic width, round cap/join and original local geometry retained. [Contour tests](../../../tests/unit/chrona/presentation/layout/test_filled_contour.py): nonzero union, overlap, holes, quadratics and deterministic order. | — |
| 2 | The mark contrast gate judges the stroke against the ground when the fill is below the floor (the primitive's own edge), Scene-checkable. | met | [Contrast integration cases](../../../tests/integration/test_point_glyph_role_outline.py): the original fill fails the floor without the contour; the added stroke wins against an external ground and reaches 3:1. SVG assertions identify that exact primitive. | — |
| 3 | Absent stroke binding is byte-identical. Synthetic fixture test. | met | [Byte/refusal integration cases](../../../tests/integration/test_point_glyph_role_outline.py) compare complete serialized Scene and actual SVG bytes to independently frozen pre-#1287 Scene projection from `8ba462d8`, with no added Layout contour. The same inputs cover lane/automatic × inline/catalogue × absent/stroke-only/outline-pattern (12 cases), without normalization. Width-without-ink retains its existing refusal. | — |
| 4 | Do not edit `examples/**`; the reviewer adopts it in slide 25. | met | [Published scope](https://github.com/tya5/chrona/issues/1287#issuecomment-6088427990) excludes authored examples and generated evidence. Adoption remains reviewer-owned. | — |

## Programme-level criteria (optional)

Current integration batch: 79 passed (44.58s), including independent frozen
projection comparisons, the merged legend warning correction, hosted identities,
real quadratic-hole decoding and both technical-print regressions. No schema,
authored examples, generated or workflow changes are included. The archive batch
and final #1327 acceptance table are separately committed documentation units.
[Lane footprint/port test](../../../tests/unit/chrona/presentation/layout/test_point_outline.py) retains the completed gate width rather than planned-role fallback and keeps semantic ports on the original part. [Projection test](../../../tests/unit/chrona/presentation/scene/test_mark_geometry.py) separates intrinsic catalogue finish metadata from a role-bound outline.

## Architecture conclusion

Layout completes union geometry, widths, footprints and clips; Scene resolves role ink and ordinary finish, forwarding catalogue width/cap/join only as an intrinsic tuple. Source parts and local geometry remain intact; an opted-in contour can enlarge the visible footprint and change downstream allocation/translation under existing rules. No Scene grammar or renderer geometry decision is added. Built-ins, stroke-only glyphs, outline-pattern ghosts and non-point consumers retain their existing treatment. Independent read-only review found no concrete ownership defect.

Predecessor public effects at head `88729d8e` on base `127392c4`:
[independent audit](https://github.com/tya5/chrona/pull/1331#issuecomment-6093939225)
and [PR count table](https://github.com/tya5/chrona/pull/1331)
discloses six changed SVG/Scene pairs and 39 unchanged pairs, including #12's
182px lane-height growth and `eps-bustest` suppression. All 65 added contours
match actual SVG path/paint/width; original Symbol parts remain. These collateral
effects require an explicit review disposition, not a no-regression claim.
[The subsequent b55 audit](https://github.com/tya5/chrona/pull/1331#issuecomment-6094139996)
on base8388 checks 101 paths / 46 slides: seven changed pairs and 39 unchanged,
including seven roadmap outlines and 14 rerouted relations. It too is predecessor
evidence after the #1214 adoption; fresh current-head comparison is required.

Required release evidence: accept/dispose disclosed effects; fresh exact-head snapshot/checks;
automatic sync and successful containing-review exact-main three-OS release.
