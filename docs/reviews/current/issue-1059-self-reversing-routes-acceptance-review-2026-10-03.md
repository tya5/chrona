<!-- chrona:literal-acceptance/v1 -->

# Issue #1059: relation routes never reverse over their own line, acceptance review

Source: [Issue #1059](https://github.com/tya5/chrona/issues/1059), re-fetched 2026-10-03 after the merge (body unchanged, four acceptance bullets; two comments, both this work's claim and status lines; no new rows). Work record: [issue-1059-self-reversing-routes-2026-10-03.md](../planning/active/issue-1059-self-reversing-routes-2026-10-03.md).

Slice: [PR #1069](https://github.com/tya5/chrona/pull/1069) (`05666fce`), CI green before merge (conformance, three pytest shards, newest-Python reproduction, derived-ready). Committed state read on the derived commit `730bc5b9`.

## Literal issue acceptance

### Issue #1059

- Source: [Issue #1059](https://github.com/tya5/chrona/issues/1059)
- Observed: 2026-10-03

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | A general route invariant, enforced in Layout and tested: no emitted relation path has three consecutive points that are collinear with opposite directions; more generally, no segment overlaps a previous segment of the same path. | met | [`routing.py`](../../../src/chrona/presentation/layout/routing.py): `route_self_overlaps` is part of `relation_route_quality` and of the lane selector (an otherwise acceptable overlapping route is refused as `no-route-found` / `E_LAYOUT_ROUTE_SELF_OVERLAP`); `repair_self_reversal` turns a reversal into an honest jog or leaves it to be refused. [`test_relation_route_invariant.py`](../../../tests/unit/chrona/presentation/scene/test_relation_route_invariant.py) asserts it on the published Scene; mutations (repair disabled; repair and invariant disabled) each fail 7 tests. | none |
| 2 | Synthetic fixtures: a source dropping inside the stub distance and the mirrored `end` case; a gate source and a bar source; a case where (a) fits; a case where only the fallback (c) fits under `maxBends`. Each asserts the invariant and an entry that is horizontal at mid-height whenever a non-reversing route exists. | narrowed | The fixtures exist in [`test_relation_route_invariant.py`](../../../tests/unit/chrona/presentation/scene/test_relation_route_invariant.py): gate source across six window and gap pairs (invariant and horizontal entry asserted), bar source and mirrored end (invariant asserted), the repair as an extra bend, and the fallback below the needed `maxBends`. The horizontal-entry half is not asserted, and not always achieved, for bar sources and the mirrored end: on target B `optics-detector` still ends vertically and five relations that ended horizontally before now end vertically (the repair finds no free jog). | [#1072](https://github.com/tya5/chrona/issues/1072) |
| 3 | A corpus gate (Scene-derived) counts self-reversing relation paths; it must be 0 after regeneration. | met | Typed error `E_SCENE_RELATION_PATH_REVERSES` in [`perceptibility.py`](../../../src/chrona/presentation/scene/perceptibility.py) runs in the existing `scene-perceptibility` conformance check over every manifest Scene ([`test_perceptibility.py`](../../../tests/unit/chrona/presentation/scene/test_perceptibility.py) covers the adjacent reversal, a later overlap and the legend-swatch exclusion). Before the fix the committed Scenes held 58 reversing paths; on the committed Scenes at `730bc5b9` `tools/check_scene_perceptibility.py` reports 54 scenes, 0 errors. | none |
| 4 | Target B, regenerated: `pdr-structure`, `optics-detector`, `delivery-integration` and `psr-shipment` show no tail behind the arrowhead. | met | Images read at 4x before and after: all four are free of the tail. `pdr-structure`, `delivery-integration` and `psr-shipment` now jog and enter horizontally; `optics-detector` drops onto the bar corner (see row 2). Points of the [committed Scene](../../../examples/halcyon-1/generated/21-target-b.scene.json) contain no overlap (row 3). | none |

## Programme-level criteria (optional)

None.

## Architecture and release conclusion

Layout owns routes and the repair; Scene only observes the finished path; no schema, View, Theme or Project change; no corpus datum edited. Only the 58 paths that reversed changed (43 slides); paths ending horizontally 335 to 330, total bends 964 to 1073 (each repaired path gains its jog).

Disclosures:

- Images read: the four target-B relations at 4x, and before/after tiles for the changed relations of controller-z annotations (one per identical-change group of 28), controller-z-ja executive, programme board, image notes, editorial lanes, tvac-slip, mission brief and overlay briefing. Not read image by image: the other halcyon gallery variants (13, 14, 17, 18, 19, 20, 08, 09, 12) and the remaining controller-z slides, which were measured (58 paths, each reversing before and clean after).
- Honest comparison with the target mock: where the repair finds a jog the arrow enters along the bar as in the mock; where it does not the old vertical corner entry returns (row 2, #1072); abutting chains are #1060.

Exact review-bearing-main three-OS CI must pass before closing #1059; that run is recorded in the closing comment.
