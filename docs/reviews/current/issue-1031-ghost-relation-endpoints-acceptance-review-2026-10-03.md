<!-- chrona:literal-acceptance/v1 -->

# Issue #1031: baseline ghosts are not relation endpoints, acceptance review

Source: [Issue #1031](https://github.com/tya5/chrona/issues/1031), re-fetched 2026-10-03 after the merge (body unchanged since filing; comments: this work's claim and state lines, no new acceptance rows). Work record: [issue-1031-ghost-relation-endpoints-2026-10-03.md](../planning/active/issue-1031-ghost-relation-endpoints-2026-10-03.md).

Slice: [PR #1032](https://github.com/tya5/chrona/pull/1032) (`615d3c27`), CI green before merge (conformance, three pytest shards, newest-Python reproduction, derived-ready).

## Literal issue acceptance

### Issue #1031

- Source: [Issue #1031](https://github.com/tya5/chrona/issues/1031)
- Observed: 2026-10-03

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | With baseline ghosts shown (in any row mode), relations connect only primary (current plan) marks, and ghost instances are never relation endpoints. A synthetic test with ghosts plus two related items asserts exactly one relation path per relation. | met | [`test_relation_ghost_endpoints.py`](../../../tests/unit/chrona/presentation/scene/test_relation_ghost_endpoints.py): two related items with snapshot ghosts, composed by the real projection and routed by the real surface composer in automatic, grouped, lanes and explicit rows (one path, no `snapshot` id), plus a scenario ghost and the snapshot-only fallback; the mutation that empties the comparison kinds fails 5 of 6. | none |
| 2 | The committed `21-target-b` Scene has 24 relation paths, one per relation, with no relation id containing `snapshot`. | met | Before: 96 relation paths for 24 relations, 72 with a `snapshot` id (plus the legend swatch, which is not a relation). After (derived-sync regeneration, not edited): 24 `relation:` paths, no `snapshot` id; also asserted in-test by [`test_relation_paths_corpus.py`](../../../tests/integration/test_relation_paths_corpus.py), which renders the slide. Before/after image read: the clustered arrowheads at every bar start and the heavy bundles are gone. | none |
| 3 | Every other committed slide keeps one path per relation. A corpus check fails if any relation produces more than one path. Duplication should never be silent. | met | The corpus sweep of all 53 committed Scenes found three more duplicating slides (not only target B): `halcyon-1/tvac-slip` and `halcyon-1/flight-readiness` (scenario ghosts) and `controller-z/baseline-ghosts`; all now draw one path per relation and every other slide was already one-to-one. New Scene error `E_SCENE_RELATION_PATH_DUPLICATE` ([`perceptibility.py`](../../../src/chrona/presentation/scene/perceptibility.py)) runs in the existing `scene-perceptibility` conformance check over every manifest Scene and in draft feedback; [`test_perceptibility.py`](../../../tests/unit/chrona/presentation/scene/test_perceptibility.py) covers it and its legend-swatch exclusion (the mutation dropping the exclusion fails). | none |

## Programme-level criteria (optional)

None.

## Architecture and release conclusion

Layout owns the routes and now skips comparison row members (`snapshot`, `scenario`) as relation endpoints; Scene only observes completed facts for the new error; no schema, View, Theme or Project change, no corpus datum edited.

Disclosures:

- Four slides changed, not one. Images read before and after:
  - `target-b`: duplicate arrowheads and line bundles removed. Honest comparison with the target mock `02-programme-board.png`: dependencies are now single lines, but three of them (`pdr -> structure`, `structure -> avionics`, `eps -> avionics`) still drop onto the bar's top-left corner from above where the mock enters horizontally at mid-height; that is #1030 (optional policy `relationRouting.entry`), not this bug. The mock's baseline ghost offsets and other target details are outside this issue.
  - `tvac-slip`, `flight-readiness`, `controller-z/baseline-ghosts`: overlapping duplicate paths and arrowheads removed; nothing else moved.
- An object with no plan instance (a snapshot-only explicit row) keeps its relation to the comparison instance; reverse by removing the `or entries` fallback.
- `test_flight_readiness_public_artifact_exercises_advanced_contracts` asserted four `marker-end` markers, i.e. the duplicated paths; it now asserts one, with the reason in a comment.

Exact review-bearing-main three-OS CI must pass before closing #1031; that run is recorded in the closing comment.
