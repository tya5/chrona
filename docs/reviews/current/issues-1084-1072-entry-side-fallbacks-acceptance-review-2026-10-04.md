<!-- chrona:literal-acceptance/v1 -->

# Issues #1084 and #1072: entry side fallbacks, acceptance review

Sources: [Issue #1084](https://github.com/tya5/chrona/issues/1084) and [Issue #1072](https://github.com/tya5/chrona/issues/1072), re-fetched 2026-10-04 after the merge (bodies unchanged; comments are this work's claims and status lines only; no new rows). Work record: [issue-1084-1072-entry-side-fallbacks-2026-10-04.md](../planning/active/issue-1084-1072-entry-side-fallbacks-2026-10-04.md); living contract [Specification 50](../../specification/50-constraint-driven-gantt-surface-quality.md) section 3.3.

Slices: design [PR #1104](https://github.com/tya5/chrona/pull/1104) (`652272b0`); code [PR #1107](https://github.com/tya5/chrona/pull/1107) (`92a63645`), CI green before merge. The corpus twin tests of this review are added by the review PR. Committed state read on the derived commit `12175e6a`.

## Literal issue acceptance

### Issue #1084

- Source: [Issue #1084](https://github.com/tya5/chrona/issues/1084)
- Observed: 2026-10-04

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | Decide how the back-route relates to `maxDetourRatio` (the reviewer's profile value, or a separate bound for the fixed back-route shape). | met | Decided and recorded on the issue and in the work record (owner-level call, reversible): the back-route's detour is measured against the shortest route that keeps both stubs (ratio 1 by construction), so the declared `maxDetourRatio: 2` admits it; no new knob. [`surface_routes.py`](../../../src/chrona/presentation/layout/surface_routes.py) `back_route`; [`test_relation_entry_back_route.py`](../../../tests/unit/chrona/presentation/scene/test_relation_entry_back_route.py) `test_the_declared_detour_ratio_of_two_admits_the_back_route_1084`; the mutation back to the bare distance fails it. | none |
| 2 | Reduce the corridor fallbacks, for example by choosing the exit stub side or length around a label, with synthetic fixtures for a label beside the source end and a ghost mark in the gap. | narrowed | Fallbacks reduced: the back-route is now tried whenever the selected route does not enter along the bar (the 8 `forward-side-entry-failed` target-B paths) and every fallback carries a reason (`reason=` in `I_LAYOUT_RELATION_ENTRY_FALLBACK`); forced `entry: side` on target B went from 14 to 23 of 24 horizontal entries. Fixtures exist for a mark in the exit stub (a proxy for a delta label), a mark in an intermediate row and the reason codes ([`test_relation_entry_back_route.py`](../../../tests/unit/chrona/presentation/scene/test_relation_entry_back_route.py)); a text label and a baseline ghost in the gap are not exercised, and no alternative exit stub side or length was built. | [#1120](https://github.com/tya5/chrona/issues/1120) |
| 3 | Target B regenerated with `entry: side` shows the 11 paths entering from the side or each fallback explained by a diagnostic. | met | Target B itself still declares `side-when-free` (the reviewer's YAML, not edited); [`test_entry_side_corpus.py`](../../../tests/integration/test_entry_side_corpus.py) renders a copy whose Layout declares `entry: side` with the declared `maxBends` 4 and `maxDetourRatio` 2 and asserts at least 22 of 24 relation paths enter horizontally and every other one carries a fallback diagnostic: measured 23 of 24, the one fallback is `tvac-emc` (`entry-stub-blocked`). For the reviewer's YAML: `entry: side` is the only value target B needs. | none |

### Issue #1072

- Source: [Issue #1072](https://github.com/tya5/chrona/issues/1072)
- Observed: 2026-10-04

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | Synthetic fixtures (bar source, gate source, mirrored end) assert both no self-overlap and a horizontal entry whenever one exists within `maxBends`. | narrowed | The ordering rule is unit-tested ([`test_stub_pair_order.py`](../../../tests/unit/chrona/presentation/layout/test_stub_pair_order.py), mutation-checked) and the gate source asserts no overlap and a horizontal entry ([`test_relation_route_invariant.py`](../../../tests/unit/chrona/presentation/scene/test_relation_route_invariant.py)); bar and mirrored-end fixtures assert the invariant only, and no synthetic Project reproduces the `optics-detector` geometry (180 scanned variants gave the same result with and without the new order), so that case is covered by a corpus twin test on target B ([`test_entry_side_corpus.py`](../../../tests/integration/test_entry_side_corpus.py)). | [#1120](https://github.com/tya5/chrona/issues/1120) |
| 2 | The five relations are measured before and after on the corpus with images read. | met | Measured on the committed Scenes ([`21-target-b.scene.json`](../../../examples/halcyon-1/generated/21-target-b.scene.json) and the other halcyon-1 and controller-z Scenes), before the self-reversal fix (`7ea931bb`) against now: relation paths ending horizontally 335 to 337; 6 gained, 4 lost; the 4 lost are one relation, `bustest-integration`, on four slides (a gate dropping onto the start corner). Target B alone: 13 to 15 horizontal (`optics-detector`, `avionics-bustest`, `mcs-comms` gained); `optics-detector` now enters horizontally with 4 bends under the declared `maxBends`. Images read: before and after tiles of `bustest-integration` on the programme board (the old tail-and-corner entry against a plain corner drop) and of the `optics-detector` change on target B; the three other slides carrying `bustest-integration` (gate glyphs, text compression, vertical group tags) were measured, not read. | none |

## Programme-level criteria (optional)

None.

## Architecture and release conclusion

Layout owns the candidate order, the back-route and its bound; Scene carries the points and the info diagnostic; no schema, View, Theme or Project change; no corpus datum edited. Default-policy corpus effect of the code PR: 12 of 613 relation paths on 6 slides (relation paths ending horizontally 351 to 358).

Disclosures:

- Target B's own YAML still declares `side-when-free`; row 3 of #1084 is shown by rendering a copy.
- An early version of the pair order promoted the source's far-side exit through its own bar and drew lines across bars on the editorial galleries; the merged code keeps that exit out of the promoted group (a `through_body` flag, unit-tested).
- Images for the code PR itself were read for one slide per identical-change group (target-b, programme board, overlay briefing, text compression and the forced-`side` target-B board); the other changed slides were measured only (listed in the work record).

Exact review-bearing-main three-OS CI must pass before closing #1084 and #1072; that run is recorded in the closing comments.
