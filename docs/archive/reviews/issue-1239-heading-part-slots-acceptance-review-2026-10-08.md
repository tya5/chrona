# Heading part slots acceptance review

<!-- chrona:literal-acceptance/v1 -->

Implemented by [PR #1240](https://github.com/tya5/chrona/pull/1240), merged as
[`a7af6eb001cdcdb29c6a4fba3df740c6086dcc9f`](https://github.com/tya5/chrona/commit/a7af6eb001cdcdb29c6a4fba3df740c6086dcc9f)
from ready base `3e7a57db1cf4b148b6ee6d4c896708f86f9cea69`. The exact published
main containing the implementation and original literal acceptance table is
[`ba679506c1c8d4661004a480b704530830ea0488`](https://github.com/tya5/chrona/commit/ba679506c1c8d4661004a480b704530830ea0488).
Split runs retain numeric spacing through native block measurement; placements
consume the closed stack baseline and baseline-minus-font-size bounds.
[Living design, architecture review and plan](https://github.com/tya5/chrona/issues/1239#issuecomment-6059626833).

## Literal issue acceptance

### Issue #1239

- Source: [Issue #1239](https://github.com/tya5/chrona/issues/1239)
- Observed: 2026-10-08

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| --- | --- | --- | --- | --- |
| 1 | Title and subtitle sourced by two different slots render in those slots' bounds with their own roles. | met | [Actual timeline SVG and slot-bound assertions](../../../tests/integration/test_heading_part_slots.py); [network SVG, roles and native owners](../../../tests/integration/test_network_heading_parts.py). | none |
| 2 | `source: heading` is byte-identical. | met | [Whole `heading` alias versus existing `title`: exact SVG and Scene surface bytes](../../../tests/integration/test_heading_part_slots.py). Authored resource provenance differs deliberately; legacy network ignored View copy is also byte-characterized. | none |
| 3 | A part sourced twice is a profile error at its pointer. | met | [Exact later `/source` pointers, whole/part overlap and resolved inherited claims](../../../tests/unit/chrona/presentation/layout/test_intent_profile.py). | none |
| 4 | Marquee places only the title inside the sign. | met | [Neutral real bulb-sign SVG and PNG](../../../tests/integration/test_heading_part_slots.py): title contained, kicker/subtitle outside. Both actual images inspected; SVG raster and PNG are pixel-identical. Actual #1233 adoption belongs to reviewer per board. | none |

## Programme-level criteria (optional)

Combined focused heading/profile/source/network, Layout/Scene boundary,
module ownership, vocabulary, text-stack and allocation tests: 356 passed.
Schema equivalence L1/L2/L3,
schema annotations, role-consumer and semantic reachability checks passed.
Whole-title composition, legacy network title placement and routes remain on
their existing paths. Split placements consume closed measured bounds/baselines;
Scene only projects identities, ownership and paint. No examples or generated
outputs were authored. Unallocated copy does not require unused typography.

## Published verification

- Exact-head PR CI [run 37788576066](https://github.com/tya5/chrona/actions/runs/37788576066), on PR head `64d1a75336e86f8b2a70e15cac4d4ae8f96fa693`: pytest shards 1–3, conformance, MCP-floor tests, derived-preview and newest-Python public-materializer reproduction succeeded. The three successful shard commands were `pytest -n 4 --dist worksteal --splits 3 --group 1 --splitting-algorithm least_duration -m "not corpus"`, and the same command with `--group 2` and `--group 3`; `python conformance/run_conformance.py` also passed.
- Shared snapshot [artifact 11556495554](https://github.com/tya5/chrona/actions/runs/37788576066) (`derived-snapshot-64d1a75336e86f8b2a70e15cac4d4ae8f96fa693`), GitHub artifact digest `sha256:ae4f18ea2d3864aebaaf2527a8f63563936e64fbef087151356d74b58708c1c3`: 145 generated paths audited; 68 SVG and 68 Scene outputs were byte-identical, with zero additions/removals. The only logical deltas were four guarded diagnostic-inventory sites and four source-vocabulary coverage updates; reports and derived path sets were checked.
- Exact published-main [three-OS release run 37794728664](https://github.com/tya5/chrona/actions/runs/37794728664), on `ba679506c1c8d4661004a480b704530830ea0488`: Ubuntu, Windows, macOS, MCP-floor and newest-Python reproduction all succeeded (50m53s, 55m14s, 20m23s for the OS jobs, respectively).
- [Issue #1239](https://github.com/tya5/chrona/issues/1239) was deliberately closed after the review and release evidence were published. Reviewer-owned Marquee YAML adoption remains with the successor per board; it is not a deferred literal criterion in this review.
