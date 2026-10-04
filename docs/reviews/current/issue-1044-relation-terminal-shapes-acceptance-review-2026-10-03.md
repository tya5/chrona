<!-- chrona:literal-acceptance/v1 -->

# Issue #1044: new relation terminal shapes and centred round terminals, acceptance review

Source: [Issue #1044](https://github.com/tya5/chrona/issues/1044), re-fetched 2026-10-03 after the merge (body unchanged; comments: this work's claim, decision and status lines, no new acceptance rows). Work record: [issues-1042-1046-1044-relation-terminals-and-rounded-routes-2026-10-03.md](../planning/active/issues-1042-1046-1044-relation-terminals-and-rounded-routes-2026-10-03.md).

Slices: design [PR #1058](https://github.com/tya5/chrona/pull/1058); implementation [PR #1075](https://github.com/tya5/chrona/pull/1075) (`d5e77f90`), CI green before merge (conformance, three pytest shards, newest-Python reproduction, derived-ready).

## Literal issue acceptance

### Issue #1044

- Source: [Issue #1044](https://github.com/tya5/chrona/issues/1044)
- Observed: 2026-10-03

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | The five shapes exist in the Theme marker vocabulary and the schema description, with synthetic geometry tests: notch present, rounded corners, single barb, two chevrons, dot diameter. | met | [`relation_terminals.py`](../../../src/chrona/presentation/layout/relation_terminals.py) and the `shape` enum and description in [`theme-v0.13.schema.yaml`](../../archive/schemas/theme-v0.13.schema.yaml) (widened in place, one expected-delta entry, `schema_equivalence` PASS), policy [`declared-vocabulary-policy-v0.1.yaml`](../../../conformance/declared-vocabulary-policy-v0.1.yaml). [`test_relation_terminals.py`](../../../tests/unit/chrona/presentation/layout/test_relation_terminals.py): notch on the axis inside the head, three rounded corners inside the box, one barb on the left, two open chevrons, dot diameter `min(L, W)`. Four geometry mutations each fail a test and were restored. | none |
| 2 | Each shape renders identically in SVG and PNG, and the legend draws the same key. | met | [`test_relation_terminals.py`](../../../tests/unit/chrona/presentation/layout/test_relation_terminals.py): for every shape the SVG marker path is exactly the Layout outline and the resvg PNG of that SVG shows ink; a parametrized test asserts the legend swatch carries the same outline and paint mode. PNG is the SVG through resvg by construction; Typst and TikZ already reject any marker (`E_VISUAL_CAPABILITY_UNSUPPORTED`), unchanged. | none |
| 3 | Round terminals are centred on the endpoint at mid-height and touch the line. A Scene test checks that the circle centre equals the endpoint, at the bar's vertical centre for spans, and that the first route point lies on the circle's edge. This holds for downward, upward and horizontal exits. | met | [`test_relation_round_terminals.py`](../../../tests/unit/chrona/presentation/scene/test_relation_round_terminals.py): the centre derived from the completed Scene facts equals the span's end/start edge at mid-height for `circle`, `open-circle`, `dot`; first and last route points are one radius from it; downward, upward and horizontal exits; triangular heads stay untrimmed. Mutations (no trim at either end, no per-end reference) fail 6 of 7. Limit: a leg shorter than the radius shifts by half the leg (one committed path, `11-overlay-briefing` `tvac-emc`, 0.45 px), so the circle is not exactly centred there. | none |
| 4 | #1042 (hollow triangle) is fixed separately; this issue does not depend on it. | met | Fixed in [PR #1068](https://github.com/tya5/chrona/pull/1068), reviewed in [issue-1042 review](issue-1042-open-triangle-terminal-acceptance-review-2026-10-03.md). | none |

## Programme-level criteria (optional)

None.

## Architecture and release conclusion

Layout owns marker outlines, the per-end marker reference and the route trim; Scene carries `points` and markers; adapters serialize. Composition with the #1059 self-reversal repair: the trim runs after it and only moves end points inward along their own leg.

Disclosures:

- Corpus: every slide with relations changes, because every committed Theme uses a `circle` source terminal. Locally regenerated, grouped by identical change (route points only, first point moved by the circle radius): 224 paths down (r 2.5), 105 down (r 4), 108 right (2.5), 53 right (4), 43 up (2.5), 26 up (4), 2 left (2.5), 1 limited (0.45), plus target-b `delivery-integration` with unchanged points. Images read for each direction group: `aster-ssd/overview` (down), `controller-z-ja/axis-secondary` (right and up), `halcyon-1/16-gallery-editorial-lanes` (left), `halcyon-1/11-overlay-briefing` (limited), `halcyon-1/21-target-b` (down, circle now on the bar's end edge). Not read: the other slides, which carry the same groups.
- The existing `circle` outline is a four-quadratic approximation that draws as a rounded square, not a true circle. That is the pre-existing outline, outside these rows; no duplicate issue was found when searching open and closed issues for it, and it is noted here as a possible successor for the reviewer.
- `attachmentOffset` is superseded for round shapes (the centre rule fixes the placement); no committed Theme declares a non-zero value for them.

Exact review-bearing-main three-OS CI must pass before closing #1044; that run is recorded in the closing comment.
