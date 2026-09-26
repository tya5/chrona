<!-- chrona:literal-acceptance/v1 -->

# Release Review — Group Bands and Headers (#481)

**Reviewed product:** `cd07bcd4` on `main` (the branch commit `57753800`, cherry-picked and split: correction `c58d7611`, then code `cd07bcd4`; the integrated evidence was regenerated on the 22-slide corpus, and the Controller Z `progress-track` Theme received the same `groupHeader` role). **Design:** [design](../../design/issue-481-group-bands-and-headers-design-2026-09-26.md), [architecture review](issue-481-group-bands-and-headers-architecture-review-2026-09-26.md), [design correction](../../design/issue-481-group-bands-and-headers-correction-2026-09-26.md), Specification 45, Specification 50 §3.4. **Implementation:** one commit, `57753800`, implementing all three approved contracts together (they share one function in `surface_composer.py`); see the commit message for the per-contract breakdown in lieu of separate slice reviews. **CI:** [four-job CI run 36249144076](https://github.com/tya5/chrona/actions/runs/36249144076) on `cd07bcd4`, green: three-OS conformance/full pytest/wheel and newest-Python public materializer reproduction.

## Literal issue acceptance

### Issue #481

- Source: [Issue #481](https://github.com/tya5/chrona/issues/481)
- Observed: 2026-09-26

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | Row stripes and group bands can be combined across the whole surface: stripes above group bands, or group bands as outlines or header-only. | met | `compose_surface_layout` emits group bands before row stripes, so a row stripe at the same declared Theme `backgroundPaintOrder` (the default in every shipped preset) is the later, topmost Scene primitive. [`test_row_stripes_paint_above_group_bands_across_the_whole_surface`](../../../tests/integration/test_render.py) fails before and passes after, asserting Scene `paint_order`/primitive-list position and that the stripe's bounds reach the timeline's far edge. The outline and header-only techniques were already reachable via existing Theme tokens (`backgroundTreatment: outline`; `groups: none`); confirmed unchanged by rendering a copied `control-room-dark` preset with `group-band.backgroundTreatment: outline` over `rowBand: both`. | — |
| 2 | A group's band includes its own header row, under both `all` and `alternate`. | met | `GroupPlacement.content_bounds` folds in the group's own header block; the independent `groupHeaderBand` shape is gated so it never double-paints a group's own now-header-inclusive band ([design correction](../../design/issue-481-group-bands-and-headers-correction-2026-09-26.md)). [`test_group_band_includes_its_own_header_row_under_all_and_alternate`](../../../tests/integration/test_render.py) fails before and passes after, checking both `all` and `alternate` and that an unselected `alternate` group draws no band at all. Visual evidence: [`examples/halcyon-1/generated/11-overlay-briefing.svg`](../../../examples/halcyon-1/generated/11-overlay-briefing.svg) before/after — the header row no longer reads as a separately shaded seam between groups. | — |
| 3 | `group-header:*` text uses the Theme's `groupHeader` role; a test asserts the declared weight. | met | The `place_text` call for group-header text uses `typography_role="groupHeader"` (was `"text"`). [`test_group_header_text_uses_the_groupheader_theme_role`](../../../tests/integration/test_render.py) asserts a declared `groupHeader` weight distinct from `text`'s reaches the Scene primitive; [`test_group_header_text_requires_a_declared_groupheader_role`](../../../tests/integration/test_render.py) guards against a silent fallback (`E_THEME_ROLE_REQUIRED`). Nine Theme files that previously relied on the fallback now declare the role: [`elevated-light`](../../../src/chrona/resources/presets/bundles/elevated-light/theme.yaml)/[`executive-light`](../../../src/chrona/resources/presets/bundles/executive-light/theme.yaml) preset bundles and seven `examples/*` themes. Visual evidence: `control-room-dark`'s `group-header:*` text renders bold (weight 700) instead of regular (400) in every affected scene. | — |

## Programme-level criteria (optional)

- The reproduction from the issue is closed end to end through the CLI: a copied `control-room-dark` preset with `rowBand: both, groupBand: both, groups: all, rows: alternate` shows an alternating row stripe painted over a distinctly-coloured group band across the full table-and-timeline surface, and the group's own header row shares the group's tint (PNG crops inspected, not committed).
- Before/after PNG crops of `examples/halcyon-1/generated/02-programme-board.svg` and `11-overlay-briefing.svg` were inspected: group-header text is bold in `control-room-dark`-derived scenes, and the group band now visually includes its own header row with no separate seam.
- CI: [four-job CI run 36249144076](https://github.com/tya5/chrona/actions/runs/36249144076) on `cd07bcd4`, green: three-OS conformance/full pytest/wheel and newest-Python public materializer reproduction.
- Public evidence changed only as attributed in the implementation commit message:
  - a group band's block-start moving up by `timeline.groupHeader.blockSize` in every affected slide (`aster-ssd/overview`, `controller-z-ja/executive`, `controller-z/{annotations,composition-compact,elevated,executive,icons,material-icons,plan-only}`, `halcyon-1/{02-programme-board,04-tvac-slip,11-overlay-briefing}`, `orion-asic/gates`);
  - `group-header:*` text weight/size (Theme-declared, per file).
- Local verification: `tests/unit/chrona/presentation tests/integration tests/cli` — 768 passed, 1 skipped; `conformance/run_conformance.py` — all checks PASS, including `presentation-contrast` (0 errors, corpus-wide five-decoration witness) and `presentation-coverage`.

## Architecture conclusion

All three fixes live in Layout (`surface_composer.py`'s `compose_surface_layout`), matching AGENTS.md layer ownership: View's `backgroundDecoration` and Layout Profile's `backgroundExtents` keep their existing schemas and meaning; Theme keeps `backgroundTreatment`/`backgroundPaintOrder`/typography-role tokens. No schema, adapter, or Scene-construction-path change.

One implementation-time finding required a design correction, published alongside this review: `_validate_background_shapes` needed a narrow exemption for a group's own `groupBand`/`groupHeaderBand` pair (Contract 2 makes them one group's two decoration layers, not two conflicting ones), and `tools/presentation_contrast.py`'s five-decoration witness needed to become corpus-wide and treat `{group-band, group-header-band}` as one concept, since Contract 2 makes their co-occurrence in one scene structurally impossible by design. Both are documented in [the design correction](../../design/issue-481-group-bands-and-headers-correction-2026-09-26.md).

Out of scope, and not left silent: no public preset or example currently demonstrates the header-only technique (`groups: none`) on its own — it was previously demonstrated only as an accidental byproduct of the double-paint this issue fixes. Adding a public example that deliberately shows it is a candidate follow-up, not required by this issue's literal acceptance, and was deliberately not forced onto an existing preset's visual identity to satisfy an internal coverage check alone.

Release disposition: all three literal rows are met.
