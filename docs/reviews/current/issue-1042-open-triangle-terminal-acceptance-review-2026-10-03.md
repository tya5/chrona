<!-- chrona:literal-acceptance/v1 -->

# Issue #1042: open-triangle terminal, acceptance review

Source: [Issue #1042](https://github.com/tya5/chrona/issues/1042), re-fetched 2026-10-03 after the merge (body unchanged; comments: this work's status lines, no new acceptance rows). Work record: [issues-1042-1046-1044-relation-terminals-and-rounded-routes-2026-10-03.md](../planning/active/issues-1042-1046-1044-relation-terminals-and-rounded-routes-2026-10-03.md).

Slices: design [PR #1058](https://github.com/tya5/chrona/pull/1058); fix [PR #1068](https://github.com/tya5/chrona/pull/1068) (`9834bd59`), CI green before merge (conformance, three pytest shards, newest-Python reproduction, derived-ready).

## Literal issue acceptance

### Issue #1042

- Source: [Issue #1042](https://github.com/tya5/chrona/issues/1042)
- Observed: 2026-10-03

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | `open-triangle` draws a **closed** outline (three edges) that is stroked, not filled. `chevron` stays an open V. | met | [`relation_terminals.py`](../../../src/chrona/presentation/layout/relation_terminals.py): `open-triangle` appends the closing edge and stays `stroke`; `chevron` keeps `move, line, line`. [`test_relation_terminals.py`](../../../tests/unit/chrona/presentation/layout/test_relation_terminals.py) asserts the command kinds and paint modes. | none |
| 2 | A synthetic test asserts that the two geometries differ: a closing segment for `open-triangle`, and none for `chevron`. A rendered SVG/PNG fixture shows both. | met | [`test_relation_terminals.py`](../../../tests/unit/chrona/presentation/layout/test_relation_terminals.py): the geometry-differs test, and `test_rendered_svg_and_png_show_the_two_shapes_differently` (the marker path of one contains `L0 0`, the other not; the resvg PNGs differ and the back edge carries ink only for the hollow triangle). The test was written first and failed 3 of 3 before the fix; reverting the one-line fix fails it again. | none |
| 3 | The Theme schema and Spec descriptions of the terminal shapes state the difference. | met | [`theme-v0.13.schema.yaml`](../../../schemas/theme-v0.13.schema.yaml) marker `shape` description and [Specification 50 section 3.3](../../specification/50-constraint-driven-gantt-surface-quality.md). `python -m tools.schema_equivalence --base-rev origin/main`: PASS (description only). | none |

## Programme-level criteria (optional)

None.

## Architecture and release conclusion

Layout owns the geometry; Scene and adapters are unchanged. No committed Theme uses `open-triangle` or `chevron`, so no committed slide changed. The terminal vocabulary was later widened by #1044 (separate review).

Exact review-bearing-main three-OS CI must pass before closing #1042; that run is recorded in the closing comment.
