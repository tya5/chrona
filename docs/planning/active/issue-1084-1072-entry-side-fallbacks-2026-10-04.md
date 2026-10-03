# Issues #1084 and #1072: relation entry side, fewer fallbacks (work record)

Living record for [#1084](https://github.com/tya5/chrona/issues/1084) (back-route detour bound and corridor fallbacks, successor of #1060) and [#1072](https://github.com/tya5/chrona/issues/1072) (find the horizontal entry when the self-reversal repair finds no jog, successor of #1059). One record because both change the same candidate order in `surface_routes.compose_surface_routes`: baseline, design plan, design, architecture review and implementation plan, published together before code. Edited in place; Git keeps history. Earlier contracts: `issue-1030-relation-entry-side-2026-10-03.md`, `issue-1059-self-reversing-routes-2026-10-03.md`, `issue-1060-relation-entry-side-backroute-2026-10-03.md`; living text in Specification 50 section 3.3.

**Scope rule:** Layout only; the reviewer's `examples/halcyon-1/*target-b*` files are not edited (their PR #1061 adopts knobs). The values target B needs are reported at the end (section 6).

## 1. Published baseline

Read on `3990b5fb` (code, the two issues, a local experiment whose generated output was not committed):

1. **`entry: side` today** (#1060): the back-route is tried only when the source does not lie strictly on the entry side of the target mark; it is checked with `relation_route_quality` (`maxBends`, `maxDetourRatio` against the bare port-to-port Manhattan distance, plus the #1059 overlap rule) and the obstacle checks; otherwise the old order.
2. **Measured on target B forced to `side`** (local, base `3990b5fb`): with the declared `maxDetourRatio: 2` only 14 of 24 paths enter horizontally. The diagnostics, with a reason added for this experiment, name three causes: `bends-or-detour` (3 paths), `forward-side-entry-failed` (8 paths: the source lies slightly left of the start, so the back-route was skipped and the forward entry had already failed) and corridor blockers (the rest).
3. **Why the ratio rejects it.** An abutting pair is 22 px apart; the mock's back-route (exit stub, drop to the gap line, across, drop, stub) is 66 px, 3 times the direct distance, because the two stubs and the sideways leg are mandatory for a side entry. Only a ratio of 3 or more admits it.
4. **#1072's case** (`optics-detector`, `side-when-free`): the source is 11.7 px left of the start, the stub candidate exists, but the pair loop is ordered by source exit first. The first source exit (`below`, nearest) with the stub target yields a route that the #1059 repair turns into 5 bends (over `maxBends` 4); the loop then moves to the next target candidate of the same source exit (the vertical `above` entry) and accepts it, never trying the source's `end` exit with the stub, which gives 4 bends. A debug run shows the 5-bend repair is forced by a blocker in the corridor at the stub tip, so no shorter repair of that route exists.
5. The `I_LAYOUT_RELATION_ENTRY_FALLBACK:<scene id>` diagnostic names no reason.

Unverified: how the new order moves the whole corpus (measured in the first slice, images read for one slide per identical-change group).

## 2. Literal acceptance (copied)

**#1084** (successor of #1060, narrowed row): target B with `entry: side` regenerated shows the 11 abutting paths entering from the side or each fallback explained by a diagnostic. Wanted: (1) decide how the back-route relates to `maxDetourRatio` (the reviewer's profile value, or a separate bound for the fixed shape); (2) reduce the corridor fallbacks, with synthetic fixtures for a label beside the source end and a ghost mark in the gap; (3) target B regenerated with `entry: side` shows the 11 paths entering from the side or each fallback explained by a diagnostic. Not in scope: the reviewer's YAML.

**#1072** (successor of #1059, narrowed row): synthetic fixtures (bar source, gate source, mirrored end) assert both no self-overlap and a horizontal entry whenever one exists within `maxBends`; the five relations that ended horizontally before #1059 and now end vertically are measured before and after on the corpus with images read.

## 3. Design plan

Use cases (synthetic Projects; target B is evidence, never the oracle): **U1** abutting chain with the back-route and `maxDetourRatio: 2`; **U2** source slightly left of the start (forward entry fails); **U3** corridor blocked by a mark in the intermediate row; **U4** a label beside the source end; **U5** the #1072 shape (the nearest exit's repaired route is over `maxBends`, another exit fits); **U6** bar, gate and mirrored `end` for U5.

## 4. Design

| Decision | Choice | Why / alternatives rejected |
| --- | --- | --- |
| Back-route trigger | The back-route is tried whenever, with `entry: side`, the selected route does not enter along the bar (last leg horizontal into the start or end, at least the entry stub long), not only when the source is not strictly on the entry side. It replaces the selected route, including a route that fell back to the first-port path. Order: forward side entry (all source exits, section below), then the back-route, then the unchanged order. | The 8 `forward-side-entry-failed` paths are exactly sources just left of the start. The old test skipped them. |
| Detour bound (owner-level call, reversible) | The back-route's detour is measured against the shortest route that keeps both stubs: `|tip.x - out.x| + |port.y - target.y| + exit stub + entry stub`, and the profile's `maxDetourRatio` applies to that. By construction the canonical shape equals it (ratio 1), so `maxDetourRatio: 2` admits it and a degenerate shape is still bounded; `maxBends` and the #1059 overlap rule apply unchanged. No new profile knob. Options rejected: exempting the back-route from the ratio (no bound at all); a separate `backRouteDetourRatio` (a knob for a number that is 1 by construction); raising target B's ratio (the reviewer would need an extreme value, 3 and more, and it would loosen every other relation). Reverse: compare against the bare distance again (one expression in `back_route`). | The ratio exists to reject wandering routes; the mandatory stubs are not wandering. |
| Reasons | `I_LAYOUT_RELATION_ENTRY_FALLBACK:<scene id>;reason=<code>` with `same-row`, `entry-stub-blocked`, `degenerate`, `bends-or-detour`, `blocked:<class>=<placement ids>` or `forward-entry-failed`. Info only; no conformance effect. | A fallback should say why, for the reviewer and for the next fix. |
| Pair order (#1072) | With `entry` `side-when-free` or `side`, every candidate pair whose target is the horizontal stub candidate is tried before any other pair, across all source exits (a `stub` flag on `ConnectorEgress`); the order inside each group is unchanged. | The nearest source exit may need 5 bends while another exit needs 4; trying only the first exit's stub forfeits the horizontal entry. |
| Not done | A route staircase shortener after the self-reversal repair: tried on the #1072 example, it finds nothing (the corridor at the stub tip is blocked), so it is not added. The remaining corridor fallbacks (an entry stub blocked by a mark beside the start, a vertical leg through another row's mark) stay diagnostics. | Minimal diff; the diagnostic names them. |

## 5. Architecture review

- **Layers.** Layout owns candidate order, the back-route and the reason; Scene carries points and the info diagnostic; no schema, View, Theme, Project or Layout Profile change (`entry: side` already exists).
- **Compatibility.** `any` is byte identical. `side-when-free` changes only where a horizontal entry exists that the old pair order skipped: measured 18 of 613 relation paths on 8 slides. `side` changes where the back-route now applies (below). Both are intended; neither is hidden behind a conditional.
- **Interaction with #1059, #1046, #1044.** The back-route and every selected route still pass `route_self_overlaps`; the path is plain orthogonal points, consumed unchanged by rounded corners and terminals.
- **Residual risks.** A new vertical leg may cross other relations (allowed today); the back-route can lengthen a short relation by its stubs (bounded by `maxBends`).

## 6. Implementation plan

| Slice | Content | Files | Evidence and gate |
| --- | --- | --- | --- |
| S1 | Trigger, bound, reasons, pair order | `layout/ports.py` (`stub` flag), `layout/surface_routes.py`, Specification 50 section 3.3, diagnostics message sentence if the registry needs one | Synthetic tests U1 to U6 (published Scene), the existing back-route tests updated for the new bound, mutation checks, `regenerate_public_examples --check` before/after, grouped corpus diff with images read (unread listed honestly), conformance |
| Review | Two literal acceptance reviews (`chrona:literal-acceptance/v1`) | `docs/reviews/current/` | exact-commit three-OS run each |

**Values target B needs (for the reviewer's YAML, reported to the lead):** `relationRouting: {maxBends: 4, maxDetourRatio: 2, entry: side}` only; no ratio change. Forced on target B with the prototype this gives 23 of 24 paths entering horizontally (14 today) with one reported fallback (`tvac-emc`, `entry-stub-blocked`); `side-when-free` gives 15 of 24 (12 today).

## 7. Corpus experiment (local, prototype, base `3990b5fb`)

Default policy (`side-when-free`, S1 prototype): paths ending horizontally 351 to 362 of 613, total bends 1173 to 1175, 18 paths changed on 8 slides. `side` forced on every slide: 351 to 455 horizontal, bends 1173 to 1432, 277 paths changed on 58 slides. Both with no self-overlap. Images and the honest list of unread slides are added in the acceptance reviews.
