<!-- chrona:literal-acceptance/v1 -->

# Issue #1060: relation entry `side`, acceptance review

Source: [Issue #1060](https://github.com/tya5/chrona/issues/1060), re-fetched 2026-10-04 after the merges (body unchanged, 4179 characters; four comments, all this work's claim and status lines; no new rows). The issue's Acceptance section lists the fixtures, five per-case assertions and the target-B line; the rows below group them. Work record: [issue-1060-relation-entry-side-backroute-2026-10-03.md](../planning/active/issue-1060-relation-entry-side-backroute-2026-10-03.md); living contract [Specification 50](../../specification/50-constraint-driven-gantt-surface-quality.md) section 3.3.

Slices: design [PR #1070](https://github.com/tya5/chrona/pull/1070) (`09f5210c`); S1 code [PR #1079](https://github.com/tya5/chrona/pull/1079) (`27df2e0e`), each with conformance, three pytest shards, newest-Python reproduction and derived-ready green before merge. Committed state read on the derived commit `07df167e`.

## Literal issue acceptance

### Issue #1060

- Source: [Issue #1060](https://github.com/tya5/chrona/issues/1060)
- Observed: 2026-10-04

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | Synthetic fixtures, checked on the published Scene: abutting finish-to-start; overlapping; the target row below the source and above it; a mirrored `end` endpoint; a gate target; the row-gap corridor blocked by a label or mark (falls back, with a diagnostic); the back-route exceeding `maxBends` (falls back). | met | [`test_relation_entry_back_route.py`](../../../tests/unit/chrona/presentation/scene/test_relation_entry_back_route.py) has one fixture for each case, routed by the real surface composer with no `examples/` input (the `maxBends` and `maxDetourRatio` limits and a mark in the way each fall back with `I_LAYOUT_RELATION_ENTRY_FALLBACK`). Two mutations (back-route disabled; obstacle check disabled) each fail tests. | none |
| 2 | For each: when a back-route fits, the last segment is horizontal at the target's mid-height and points into the start (or end); the horizontal leg lies in the row gap, outside every row's mark band; at most `maxBends` bends and no self-reversing triple; no crossing of marks or text. | met | The same tests assert the last segment and its direction for start and end, that the back leg lies between the source and target mark bands (target below and above), the bend bound and [#1059](https://github.com/tya5/chrona/issues/1059)'s overlap invariant (`reverses`), and that no segment crosses the blocking mark; the gap leg is built on the target row's edge and every segment is obstacle-checked in [`surface_routes.py`](../../../src/chrona/presentation/layout/surface_routes.py). The mark-band assertion is made for the abutting, overlapping and above cases, not separately for the gate and mirrored-end cases. | none |
| 3 | The `side-when-free` and `any` outputs are byte-identical to today's (the new value only). | met | `tools/regenerate_public_examples.py --check` passed before the merge on the default; `entry` defaults to `side-when-free` and the back-route and the gate stub are gated on the `side` value; [`test_relation_entry_back_route.py`](../../../tests/unit/chrona/presentation/scene/test_relation_entry_back_route.py) asserts the other values never back-route or report; the merged derived commit regenerated no slide of those values. | none |
| 4 | On target B with `entry: side`, regenerated, the 11 paths above enter from the side, unless a diagnostic explains a fallback. | narrowed | Target B still declares `entry: side-when-free` ([`target-b.yaml`](../../../examples/halcyon-1/layouts/target-b.yaml), the reviewer's YAML, not edited), so the committed Scene does not show it. A forced local run (see the work record section 7) on base `09f5210c`: with the declared `maxDetourRatio: 2`, 2 of the 11 paths enter from the side and 11 relations report the fallback diagnostic; with the ratio at 10, 5 enter and 8 fall back (labels and ghost marks beside the source block the exit stub or gap leg). The fallback is visible, but the paths do not enter from the side. | [#1084](https://github.com/tya5/chrona/issues/1084) |

## Programme-level criteria (optional)

None.

## Architecture and release conclusion

Layout owns the path (built, not searched) and its checks; Scene carries the points and the info diagnostic; one additive enum value in the Layout Profile (`schema_equivalence` PASS with a recorded expected delta); no View, Theme or Project change; no corpus datum edited.

Disclosures:

- Corpus experiment with `side` forced on every slide (local, not committed): relation paths ending horizontally 330 to 399 of 564, total bends 1073 to 1285, 217 paths changed on 51 slides, no self-reversing path. Images read: the forced target-B programme board (back-routes enter along the bar as the mock does). Not read image by image: the other changed slides, which were measured only.
- Honest comparison with the mock: the mock's back-route is about three times the direct distance of an abutting pair, so with `maxDetourRatio: 2` most abutting target-B chains stay on the old vertical corner entry (with a diagnostic) until the reviewer raises the ratio; #1084 covers the ratio decision and the corridor fallbacks.
- A relation that does not enter along the bar under `side` is reported by `I_LAYOUT_RELATION_ENTRY_FALLBACK` (info); it does not fail conformance.

Exact review-bearing-main three-OS CI must pass before closing #1060; that run is recorded in the closing comment.
