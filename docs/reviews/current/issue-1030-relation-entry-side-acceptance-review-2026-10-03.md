<!-- chrona:literal-acceptance/v1 -->

# Issue #1030: relation entry side, acceptance review

Source: [Issue #1030](https://github.com/tya5/chrona/issues/1030), re-fetched 2026-10-03 after the merges (body unchanged, 1209 characters; three comments, all this work's claim, decision and state lines; no new acceptance rows). The issue has no acceptance table; the rows below are its literal asks. Work record: [issue-1030-relation-entry-side-2026-10-03.md](../planning/active/issue-1030-relation-entry-side-2026-10-03.md); living contract [Specification 50](../../specification/50-constraint-driven-gantt-surface-quality.md) section 3.3.

Slices: design [PR #1033](https://github.com/tya5/chrona/pull/1033) (`fa6ba0ea`); S1 policy and rule [PR #1036](https://github.com/tya5/chrona/pull/1036) (`8277765a`, default `any`, byte identical); S2 default flip [PR #1041](https://github.com/tya5/chrona/pull/1041) (`7c7b81e3`). Each had conformance, three pytest shards, newest-Python reproduction and derived-ready green before merge.

## Literal issue acceptance

### Issue #1030

- Source: [Issue #1030](https://github.com/tya5/chrona/issues/1030)
- Observed: 2026-10-03

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | When the endpoint is `start` (or the mirrored `end`), the source lies on the approach side, the space immediately beside the endpoint at mid-height is free and a stub of at least arrowhead plus clearance fits, try the horizontal entry first; otherwise keep today's order. | met | [`ports.py`](../../../src/chrona/presentation/layout/ports.py) offers a horizontal stub candidate (length = target terminal `headLength` + max(corner radius, stroke width), inside the timeline, no mark, text or label, host exempt, from [`surface_routes.py`](../../../src/chrona/presentation/layout/surface_routes.py)) ahead of the unchanged distance order; a blocked, no-room, wrong-side or failing case falls back. [`test_relation_entry_side.py`](../../../tests/unit/chrona/presentation/scene/test_relation_entry_side.py) covers start, mirrored end, source not on the approach side, blocked corridor, no room to the timeline edge, and `maxBends`. | none |
| 2 | A declared policy (for example `relationRouting.entry` with the values side-when-free and any), default chosen on readability grounds. | met | Optional `relationRouting.entry` in [`layout-profile-v0.10.schema.yaml`](../../../schemas/layout-profile-v0.10.schema.yaml) (additive; `schema_equivalence` PASS), parsed in `engine.py`, documented in Specification 50 section 3.3; profile tests in [`test_relation_entry_profile.py`](../../../tests/unit/chrona/presentation/layout/test_relation_entry_profile.py) (absent, each value, unknown value fails at `/relationRouting/entry`). Default `side-when-free` chosen on the corpus experiment in the work record section 7: horizontal entries 183 to 333 of 557 relation paths, total bends 993 to 947, no new fallback; owner-level decision with reverse recorded on the issue. | none |
| 3 | Both branches tested on synthetic fixtures: source left with free space, source right, blocked corridor, narrow gap needing one more bend. | met | [`test_relation_entry_side.py`](../../../tests/unit/chrona/presentation/scene/test_relation_entry_side.py) runs both policy values on synthetic Projects with no `examples/` input: source left with free space (horizontal at the start's mid-height), source right (mirrored `end`), blocked corridor (shared-track mark in the stub space), no room, and a narrow gap on a long window where the horizontal entry costs exactly one bend more and falls back below that `maxBends`. Mutations (policy ignored, mirror dropped) fail tests; one equivalent mutant (the stub-free predicate, also enforced by the loop's corridor check) is disclosed in the PR. The #687 lane fixture ([`test_synthetic_lane_route_corridors.py`](../../../tests/integration/test_synthetic_lane_route_corridors.py)) that was costly only for the old order is pinned to `entry: any` and a new test shows the side entry draws it without hiding a name. | none |
| 4 | Corpus-wide diffs reviewed against #575. | met | Against [#575](https://github.com/tya5/chrona/issues/575) (corpus is not authority, no data edits, core tested synthetically): no corpus datum was edited and the rule is proved on synthetic fixtures. All 53 slides were regenerated and measured path by path (48 slides, 152 of 557 paths changed). Images read before and after for one slide per identical-change group: target-b, programme board, editorial lanes, launch campaign, tvac-slip, replan baseline, image notes, overlay briefing, controller-z annotations (the other 27 controller-z slides change the same single relation, the other halcyon galleries share the board's change). Slides not read image by image are listed in the disclosure. | none |

## Programme-level criteria (optional)

None.

## Architecture and release conclusion

Layout owns the candidate order and stub; Scene, View, Theme and adapters are untouched; one optional Layout Profile property. The committed Scenes after derived-sync (`e87836fd`): 332 of 557 relation paths end horizontally (the measured 333 differs by one path after other merged work).

Disclosures:

- Honest comparison with the target mock `02-programme-board.png`: the board now enters bar starts horizontally at mid-height as the mock does (for example Primary structure fabrication, Detector calibration, Operations rehearsals), and arrowheads no longer sit half outside bars; where the source is directly above or closer than the stub width the line still drops, and two lane relations show a small hook where the stub needs a jog (accepted extra bend, bounded by `maxBends`). The mock's other details (ghost offsets, notes) are outside this issue.
- Not read image by image: the other controller-z slides, `controller-z-ja` (2), `aster-ssd` overview, `orion-asic` gates, mission brief and its two dark/mono variants, technical print and the remaining halcyon gallery variants; they were measured, and each changes only relation paths in the way of its group's read slide.
- Default flipped for every Profile that does not declare `entry`; a Profile with `entry: any` is unchanged. Reverse: the one default in `engine.py` and `model.py`.
- The reviewer already adopted `entry: side-when-free` explicitly in target B (their YAML, not edited here).

Exact review-bearing-main three-OS CI must pass before closing #1030; that run is recorded in the closing comment.
