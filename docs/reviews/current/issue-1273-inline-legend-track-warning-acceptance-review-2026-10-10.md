<!-- chrona:literal-acceptance/v1 -->

# Acceptance review — inline legend track warning (#1273)

Implementation: [#1324](https://github.com/tya5/chrona/pull/1324) (merge `26b25c53`), checked against `origin/main` `289444de`. The minimum block of an inline (`line`) legend is one row (`layout/sources.py`), while its preferred block keeps the conservative stack, so a content-sized slot and all geometry are unchanged. Because the wrapped row count is known only once the slot's inline size is, `layout/surface_legend.py` checks the placed rows: a legend whose rows end below its slot reports `W_LAYOUT_VISIBLE_OVERFLOW` (`layout-track`, placement `legend`) with the true required block. A stacked legend keeps today's measurement. The legend grid declaration is #1290, not here. Plan: [Status comment](https://github.com/tya5/chrona/issues/1273).

## Literal issue acceptance

### Issue #1273

- Source: [Issue #1273](https://github.com/tya5/chrona/issues/1273) (body, the 2026-10-09 Sunday Strip comment, the Status comment and the reviewer pre-check)
- Observed: 2026-10-10

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | Slides 21–24 of `examples/halcyon-1` report no `layout-track` legend warning. | met | Committed derived evidence on `289444de`: `examples/halcyon-1/generated/21-target-b.scene.json`, `22-yuya.scene.json`, `23-titlecard.scene.json` and `24-marquee.scene.json` contain no `W_LAYOUT_VISIBLE_OVERFLOW` (also `25-sunday.scene.json`; count 0 in each). The reviewer pre-check on the issue (2026-10-10) found the same at 1600x900. The [PR count table](https://github.com/tya5/chrona/pull/1324) records the before values (139.2, 139.2, 121.8, 116.7 required against 22). | — |
| 2 | A test with an inline legend made deliberately too wide for one row in a one-row slot still warns, with a required block equal to its wrapped rows. | met | [`test_inline_legend_track_warning.py`](../../../tests/integration/test_inline_legend_track_warning.py) `test_an_inline_legend_too_wide_for_one_row_still_warns_with_the_block_its_rows_need` (200 px slot, 24 px block: several rows, exactly one `visible-overflow` warning, `required_block` not below the end of the wrapped labels minus the slot start, above the available 24); the same file has the one-row case with no warning and the stacked case that still warns. The test asserts the lower bound `>= needed - 1e-6`, not strict equality. The committed controller-z evidence shows the real value: `examples/controller-z/generated/region-frames.scene.json` reports `requiredBlock` 64.0 against 52.0 (the former stack value was 100.8). | — |
| 3 | Do not edit `examples/**`. | met | [Diff](https://github.com/tya5/chrona/pull/1324/files): `sources.py`, `surface_legend.py` and the test only; no `examples/**`, Scene, adapter or bot-generated file. The derived-sync regeneration of the six affected Scene JSONs is the bot's commit, as the PR body states. | — |

## Programme-level criteria (optional)

None. Every row is met; the issue can close after this review and the three-OS run on the `main` commit that publishes it are cited.
