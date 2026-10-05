<!-- chrona:literal-acceptance/v1 -->
# Issue #1167 — ordered annotation artwork layers

Published source baseline: `d02ceb370fc4ad79299db3f47e80ee330dc9de18`.
Implementation commit: `26847ccda5897837fbb6ab93662a40f3028301ac`.
[Plan, architecture review and publication receipts](https://github.com/tya5/chrona/issues/1167#issuecomment-6000054134).
Normative design was published in `8afafa734d39eb6e247eb33ae2ab2e705cb462a7`
before product changes. Theme normalizes layers; Layout completes each glyph's
geometry against the same paper box and pivot; Scene admits each typed layer
before projecting parts. Adapters remain unchanged. Named roles retain the
closed artwork paint/contrast contract and must have an actual consumer.

The new, separately pinned `chrona-annotation-parts-v2026-10` catalogue splits
mounting and rods without modifying the existing target-parts catalogue.
Importer/source reproduction and manifest identities are tested; its actual
light/dark 64px/20px SVG and packaged-font raster were reviewed.
The adapter's full synthetic SVG/raster with oppositely tilted notes was also
reviewed: mounting and rods retain separate inks, share the completed tilt,
and leave the text legible inside the frame without clipping.

Existing artwork/viewer-fit integration: 69 passed. Theme/catalogue unit tests:
32 passed. Consumer, capability and ink-ground unit tests: 63 passed. Five
pre/post characterization cases (default, tilt, absent, optional baseline,
fill-only baseline) preserve complete SVG and canonical Scene SHA-256 hashes.
Layered integration: 12 passed, including equality of every non-artwork
completed primitive. The four focused groups total 176 passing tests.
The schema-versus-token diagnostic clarification was published in
`201f2b5802ae55405a1008c9894445a32c1d41cf` before final implementation
acceptance; both boundaries are tested without changing ingress ownership.
Schema equivalence passed against ready-main
`d43cc6beaf9d7589d2686faa3c0a4ed16cb249ff`: L1 delta1/equal37, L2 411
mapped documents and L3 739 probes with no new invalid verdicts/diagnostics.
Theme-consumer and literal-review gates passed. Final
shared corpus deltas and required CI receipts belong in the linked Status.
The first CI conformance run found missing author-facing annotations on the
new schema definitions. Descriptions/examples were completed; annotation
lint and 38 annotation/Theme unit tests pass, and every schema validation
fingerprint is unchanged from the first implementation head. All other
conformance checks passed. All three pytest shards also reported the same
collection error: the new consumer test basename collided with an existing
integration module. The new file now has an artwork-specific basename, without
changing import mode or package boundaries. Their executed tests all passed
(2422/2415/2421). Corrected-head collection succeeds for all 7,322 tests;
the formerly conflicting unit/integration pair passes all 10 focused tests.
The downstream derived-ready failure reflects those upstream failures;
corrected-head CI remains a release requirement.

## Literal issue acceptance

### Issue #1167

- Source: [body](https://github.com/tya5/chrona/issues/1167)
- Observed: 2026-10-06

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| --- | --- | --- | --- | --- |
| 1 | A single-object `artwork` is unchanged. | met | Five complete pre/post SVG/Scene hash comparisons; existing integration regressions; [determinism test](../../../tests/integration/test_annotation_artwork_layers.py) | — |
| 2 | Two layers with two roles emit two Symbols in order, each with its own ink. | met | [Layer integration](../../../tests/integration/test_annotation_artwork_layers.py): exact two single-part Symbols and actual SVG order/ink; explicitly pinned mounting/rods also retain their 2+4 part order and separate inks | — |
| 3 | A missing layer role is `E_THEME_ROLE_REQUIRED` at the layer pointer. | met | [Layer integration](../../../tests/integration/test_annotation_artwork_layers.py): exact indexed pointer; malformed ingress/schema and internal token diagnostics are tested separately | — |
| 4 | Text contrast considers every layer it touches. | met | [Layer integration](../../../tests/integration/test_annotation_artwork_layers.py): swap each touched layer into the worst-ground position; existing hole, opacity, stroke and fail-closed ink-ground regressions pass | — |
| 5 | A tilt rotates all layers rigidly. | met | [Layer integration](../../../tests/integration/test_annotation_artwork_layers.py): every path point matches the shared rigid transform, preserving authored identities and order | — |
| 6 | Yuya adopts it, with a `scroll-rods` catalogue glyph. | not met | Catalogue support alone is not adoption; [reviewer-owned #1116](https://github.com/tya5/chrona/issues/1116)/[PR #1123](https://github.com/tya5/chrona/pull/1123) must supply actual YAML and rendered output | — |

## Programme-level criteria (optional)

Keep open until required release evidence and actual Yuya adoption are verified.
No examples are adapted to conceal output changes; inspect the shared CI
materializer snapshot as one batch and disclose its exact delta counts.
