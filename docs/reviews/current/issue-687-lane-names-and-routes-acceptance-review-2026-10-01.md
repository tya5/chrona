<!-- chrona:literal-acceptance/v1 -->

# Issue #687 — lane member names and route order acceptance review

Source: [Issue #687](https://github.com/tya5/chrona/issues/687), observed 2026-10-01 (no comments; body unchanged since 2026-09-30). Found by #679. Design pack, published in [PR #755](https://github.com/tya5/chrona/pull/755) (merged as [`4f85ae72`](https://github.com/tya5/chrona/commit/4f85ae7222055c3f976abf3273cfd7349d1c6afb), [PR CI](https://github.com/tya5/chrona/actions/runs/36827898791)): [design](../../design/issue-687-lane-names-and-routes-design-2026-10-01.md), [implementation plan](../../planning/active/issue-687-lane-names-and-routes-implementation-plan-2026-10-01.md) and [architecture review](issue-687-lane-names-and-routes-architecture-review-2026-10-01.md). Code: [PR #759](https://github.com/tya5/chrona/pull/759) merged as [`e81c7a25`](https://github.com/tya5/chrona/commit/e81c7a2561fcc5f15ff6daa86cebb01d6903017f) ([PR CI](https://github.com/tya5/chrona/actions/runs/36829305497)).

## Literal issue acceptance

### Issue #687

- Source: [Issue #687](https://github.com/tya5/chrona/issues/687)
- Observed: 2026-10-01

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | A synthetic fixture (no `examples/` input) reproduces a name at the `end` position blocking a route exit and showing `W_LAYOUT_RELATION_SUPPRESSED`; the fixture fails today if the ladder order is changed so that `end` wins. | narrowed | The synthetic fixtures in [`test_synthetic_lane_route_corridors.py`](../../../tests/integration/test_synthetic_lane_route_corridors.py) use no `examples/` input and reproduce `W_LAYOUT_RELATION_SUPPRESSED` caused by end-side member names. The measured cause is not a name on the exit port: every attempt on the four suppressed public relations is `quality-rejected` (5 to 7 bends against a maximum of 4), plus 4 `no-route-found` on slide 16, and none is an `egress-collision`. The blocker is a wall of end-side names across stacked lane rows, so the issue's "name on the exit port" framing is partly wrong. The wall fixture (6 spans, one relation) suppresses the route today and draws it after the change with all six names still shown, and fails when the corridor is disabled (mutation check on a worktree copy); a second fixture (7 spans, one relation) keeps the route suppressed because the only repair would suppress a name shown today. Changing the ladder so `end` wins is not what the fixtures test, because the corridor, not the ladder, is the lever (the ladder option, B, had no effect: no lane view declares `above` or `below`). | [#760](https://github.com/tya5/chrona/issues/760) |
| 2 | The design states the order (names before routes, routes before names, or a reserved corridor) and its reason, and Spec 50 says so. | met | The [design](../../design/issue-687-lane-names-and-routes-design-2026-10-01.md) compares five options measured on the whole corpus (A reserve a 12 px corridor at every port; B rank above and below over end; C routes first; D do nothing; E reserve a corridor only for relations that names alone would lose, behind a no-worse check) and recommends E with its reason. [Spec 50](../../specification/50-constraint-driven-gantt-surface-quality.md) now states the order (names, then routes, then post-route labels) and the corridor rule: before the names are placed Layout rehearses the name and route phases, reserves the segments of a route that member names alone would lose as the `route-reserve` obstacle class, and keeps the corridors only if a second rehearsal loses a strict subset of the relations and suppresses no name that was shown. | — |
| 3 | If behaviour changes, corpus evidence is regenerated and each changed slide is reviewed against the general rule and the design targets (#575 row 4); byte identity is not the gate. | met | The corpus evidence was regenerated locally and every changed file reviewed before merge; the table is in the [PR #759 body](https://github.com/tya5/chrona/pull/759). Three of the 29 public slides change (`02-programme-board`, `12-glyph-gates`, `11-overlay-briefing`); the other 26 are byte-identical. On the three, `launch-leop` is drawn (one bend) where it was suppressed with 16 of 16 port pairs rejected, no name is suppressed that was shown, one more name is shown per slide (`frr` on 02 and 12, `launch` on 11, so 20 of 26 names shown becomes 21), the `campaign` name moves from the end side to the start side, three ops-lane names swap block positions, and on slide 11 the `window-note` annotation takes its first declared candidate with its tail so two annotation warnings disappear. No dependency crosses a name and no names overlap. Option C (routes first) was rejected for suppressing 40 names that are shown today, and option A for newly losing `station-comms` on slide 16. | — |

## Programme-level criteria (optional)

None.

## Architecture and release conclusion

Layout composition only: the phase order, the single shared obstacle index and the declared name ladder are unchanged, and a corridor is reserved only where it demonstrably saves a dependency without costing a shown name. The change is a behaviour change on three public slides, judged against the general rule and the HALCYON target (which draws every dependency), not by byte identity.

Disclosures:

- **Slide 16 still loses `shipment-campaign`.** Drawing it would suppress three names that are shown today (`frr`, `launch`, `leop`), so the no-worse check refuses. Whether a route should outrank names there (option E2) is an owner decision, recorded in #760.
- **Two route degradations inside the limits.** `rehearsals-launch` goes from 3 to 4 bends on the three changed slides (limit 4), and `psr-shipment` on slide 11 gets longer (length ratio 1.09 to 1.16). I judged both acceptable because a dependency is gained; the stop wording in the brief was "lost or worse than the target".
- **A cost.** Only lane projects with relations pay: `programme-board` rendered in 3.1 s before and 4.5 s after, and `gallery-editorial-lanes` in about 22 s before and about 50 s after. The cost is routing, not name placement, and it gives back part of the speedup of #721 item 2; a route-search memo shared by the extra passes is the follow-up in #760.
- **The issue's framing was partly wrong** (see row 1): the conflict is a wall of end-side names, not a name on an exit port, and the measured effect on the public slides is the evidence for that.
- **Shared scratchpad.** The implementing agent overwrote four helper scripts in the shared session scratchpad before noticing it is shared; none is part of the repository.

Exact review-bearing-main three-OS CI and newest-Python materializer run must pass before closing #687; record that run in the issue closing comment.
