<!-- chrona:literal-acceptance/v1 -->

# Release Review — Milestone Glyph Symbols (#464)

**Reviewed product:** `f485ef9a` on `main` (I464-1..I464-4 implementation `5951dccd`; design correction `f485ef9a`). **Design:** [design](../../design/issue-464-milestone-glyph-symbols-design-2026-09-26.md), [architecture review](issue-464-milestone-glyph-symbols-architecture-review-2026-09-26.md), Specification 07 §5.2, Specification 08 §5.3. **Slice review:** [I464-1](issue-464-milestone-glyph-symbols-i464-1-review-2026-09-27.md).

## Literal issue acceptance

### Issue #464

- Source: [Issue #464](https://github.com/tya5/chrona/issues/464)
- Observed: 2026-09-27

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | A Theme can bind `milestoneSymbol` (and its actual and baseline counterparts) to a glyph asset instead of a built-in shape, and every milestone renders with it. | met | [I464-1 review](issue-464-milestone-glyph-symbols-i464-1-review-2026-09-27.md): `milestoneSymbolActual`/`milestoneSymbolBaseline` roles, `variant_symbol` fallback; `themes/12-glyph-gates.yaml` binds the glyph and every gate on the committed slide renders it. | — |
| 2 | A glyph with at least two painted parts renders both, with paints from the Theme or from the asset, and the choice is documented. | met | [I464-1 review](issue-464-milestone-glyph-symbols-i464-1-review-2026-09-27.md): the committed slide's two-part hexagon (role-coloured body, literal-coloured band); paint-source precedence documented in Specification 07 §5.2. | — |
| 3 | Planned, actual and baseline variants of one glyph can be distinguished without colour alone. | met | [I464-1 review](issue-464-milestone-glyph-symbols-i464-1-review-2026-09-27.md): the baseline variant's band strokes (hollow) instead of filling (solid), a treatment difference independent of colour. | — |
| 4 | One committed slide renders HALCYON-1 `02-programme-board` with a non-built-in gate glyph, and its evidence is reproducible. | met | [Committed Scene](../../../examples/halcyon-1/generated/12-glyph-gates.scene.json) and [SVG](../../../examples/halcyon-1/generated/12-glyph-gates.svg); `tools.regenerate_public_examples --check` reproduces all 23 slides. | — |
| 5 | Dependency arrows still end at the glyph's edge, and the perceptibility gate passes on that slide. | met | [test_glyph_gate_geometry.py](../../../tests/acceptance/output/test_glyph_gate_geometry.py): parts reach the mark's box edge at the centre line within 0.5 px; every checked route terminal lies on that edge; `evaluate_scene_perceptibility` reports 0 errors on the slide. | — |

## Programme-level criteria (optional)

- Root cause reproduced on the published baseline (`908f9d69`): binding a non-built-in `symbol` shape fails `E_THEME_SCHEMA` at Theme-schema validation, with `mark_geometry.symbol_geometry`'s own `E_THEME_TOKEN_TYPE` check as unreachable defense in depth.
- Public evidence changed only as attributed in the slice review: one new slide (`halcyon-1/glyph-gates`), and five slides sharing `wallboard.yaml` changed only their recorded theme `contentIdentity` provenance — zero primitive, paint or diagnostic differences, confirmed by structural comparison.
- `.venv/bin/python conformance/run_conformance.py`: PASS, all 31 checks, locally.
- CI: pending.

## Architecture conclusion

Theme owns the glyph's shape and per-part paint source (role colour or a literal asset colour); Scene completes a multi-part glyph as several sibling `Symbol` primitives sharing one purpose/bounds, reusing the existing per-primitive paint-completion pipeline rather than inventing a nested paint shape; Layout is unchanged, and the port-at-visual-edge guarantee rests on an authoring constraint (full-bleed `viewBox`) that is now directly tested rather than assumed; adapters needed no change. The one contrast-evaluation gap the multi-part case exposed (`_ground_under` not considering a prior `Symbol` as ground) is fixed generically, not special-cased to this glyph.

Out of scope, and not left silent (named in the [design plan](../../planning/active/issue-464-milestone-glyph-symbols-design-plan-2026-09-26.md)): state-dependent glyphs (Flat Pack's ticked/open-by-as-of gate), icon-catalogue-backed glyph parts, and clip-source use of a multi-part glyph's silhouette.

Release disposition: all five literal rows are met.
