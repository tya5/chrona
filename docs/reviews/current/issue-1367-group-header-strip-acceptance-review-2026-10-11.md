<!-- chrona:literal-acceptance/v1 -->

# Group header strip acceptance (#1367)

Implementation: `c74b6abddcd777b5c3da7ccfbd0b0d3d283286df`, based on ready main `5f2f056b`. Design and whole-architecture review: [current issue record](https://github.com/tya5/chrona/issues/1367#issuecomment-6098982235), normative Specs 07/46/50 in `75d57ca0` and pre-code absence clarification `1289779b`.

## Literal issue acceptance

### Issue #1367

- Source: [Issue #1367](https://github.com/tya5/chrona/issues/1367)
- Observed: 2026-10-11

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | In a Scene test, the strip covers exactly the header row's block extent across the declared extent. | met | [Synthetic Scene/SVG tests](../../../tests/integration/test_group_header_strip.py): `test_strip_follows_each_final_header_block_and_declared_extent_in_scene_and_svg` covers table/timeline/both; folded completion and omitted-default tests retain exact final bounds. | — |
| 2 | The text-sized band paints over it. | met | [Caption test](../../../tests/integration/test_group_header_strip.py): `test_strip_remains_full_width_around_a_text_sized_caption_band` asserts the independent full-row strip, text-sized band, matching block extent, strict Scene paint order and SVG emission order. | — |
| 3 | Body rows get no strip. | met | [Extent/no-grouping tests](../../../tests/integration/test_group_header_strip.py) assert the exact strip identities are only the completed group headers; final header bounds exclude member rows. The no-grouping case emits no strip. | — |
| 4 | Do not edit `examples/**`. Refs #1269. | met | [Implementation diff](https://github.com/tya5/chrona/commit/c74b6abddcd777b5c3da7ccfbd0b0d3d283286df) changes schema, Layout/Scene wiring, contrast coverage, synthetic tests and five tool-proven stale equivalence entries only; `git diff --name-only 5f2f056b...c74b6abd -- examples` is empty. | — |

## Programme-level criteria (optional)

**Release pending:** the fresh PR snapshot, batched public materializers/reports and exact-head gates must pass after adopting #1291's ready main. Close only with the three-OS release run on the exact published main containing this review; local tests are not that release evidence.

## Architecture conclusion

Own-worktree `.venv/bin/python -m pytest -q tests/integration/test_group_header_strip.py`: **22 passed** (19.75s). Contrast/registry/header/pattern regression batch **54 passed** (26.50s); strip-order/axis batch **57 passed** (1.86s); Scene/paint/pattern/group batch **101 passed** (9.40s). After indexed order validation, strip-order/canvas-overlay batch **21 passed** (0.98s; overlaps the earlier order batch).

`python -m tools.schema_equivalence --base-rev origin/main`: **PASS**, L1 additive=1/equal=37; L2 482 documents/378 mapped and L3 739 probes preserve known invalid fixtures. L2+L3=44.1s within 60s. `--prune-stale` separately proved and removed five already-merged View deltas; no schema behavior is removed.

Root and independent Luna review: Layout composes final/folded header geometry and validates actual same-group layers; Scene projects completed Rect/pattern geometry without measurement or order selection. Strip paint is independent of group tint and caption selection. Absent-role Scene/SVG identity, explicit-none generic absence disclosure, shared decoration-concept coverage and unrelated overlap errors remain truthful. No project-specific rule or unresolved design item.
