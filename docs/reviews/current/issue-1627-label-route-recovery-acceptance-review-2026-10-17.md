<!-- chrona:literal-acceptance/v1 -->

# Issue #1627 — label and route recovery acceptance

Candidate code `6461378b2`, regression tests `75483b89f` and `4b8253c10`;
integrated with main `ba895af3a` as `b4d2c70eb`.
Official CI must confirm the batch below before merging; exact-main release
evidence remains required before closure.

## Literal issue acceptance

### Issue #1627

- Source: [Issue #1627](https://github.com/tya5/chrona/issues/1627)
- Observed: 2026-10-17

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | Trace posted; a synthetic twin per remaining defect. | met | [Trace](https://github.com/tya5/chrona/issues/1627#issuecomment-6230332335); [neutral observable regression](https://github.com/tya5/chrona/blob/4b8253c10/tests/integration/test_neutral_point_route_label_recovery_1627.py) fails on exact parent `58d334707` (21 labels), passes on candidate (22 labels, all 31 relations, five left-port point arrivals). Unit twins cover full text/chip footprints, logical route owners, tie order, non-route blockers and unchanged final validators. | — |
| 2 | On the trial CSV, technical-print, editorial and wallboard-dark show all member labels, none overlapping its own bar, and no right-side arrival into a later-dated target, viewed as PNG. | met | Exact [trial3 inputs and commands](https://github.com/tya5/chrona/tree/dbbce45e60392b7b0be788f841fe2673f4830944/trial3), project-only renders: all three PNGs viewed; 22 names each, zero own-bar bounds overlaps, all 21 end→start and five end→at arrivals checked against typed target instances and primary-mark boundaries. No entry-policy change. [Direction finding resolved](https://github.com/tya5/chrona/issues/1627#issuecomment-6231699875). | — |
| 3 | Public SVG/Scene changes listed with counts. | met | [Batch evidence and status](https://github.com/tya5/chrona/issues/1627#issuecomment-6230332335): repository derived-workflow snapshot at `b4d2c70eb` against `ba895af3a`; per-slide counts below. Official final-head CI must confirm them before merge. | — |

## Public-output batch

50 SVG and 50 Scene pairs compared; 98 files are byte-identical. Only
`halcyon-1/16-gallery-editorial-lanes` changes. Its 238 primitives retain all
identities; no routes, labels or other primitives are added or removed.

| Slide | Changed routes | Changed member labels | Changed primitives total | Added / removed | New / removed diagnostic codes |
| --- | ---: | ---: | ---: | --- | --- |
| 16-gallery-editorial-lanes | 9 | 6 | 15 | 0 / 0 | 0 / 0 |
| Every other slide (49) | 0 | 0 | 0 | 0 / 0 | 0 / 0 |

The routing receipt changes from fallbackSearch8/shapeSettled16 in both passes
to 8/16 in the baseline and 7/17 in recovery; other diagnostic entries and
counts remain unchanged. No examples or generated outputs are PR-authored.
The changed slide was also viewed through the native PNG adapter using a
temporary immutable Context: its surfaces/diagnostics match the public Scene,
and all 26 member labels are present with zero own-mark bounds intersections.

## Programme-level criteria (optional)

75 focused checks pass after integration with the grouping fix. Require exact-head PR checks and three-OS full
pytest/conformance/wheel plus public reproduction on exact main containing this
review; keep issue1627 open until complete.

## Architecture conclusion

Spec50 owns the revised on-demand preference: initially suppressed optional
names only, one existing retry, fewest distinct logical route owners then
declared rank. Full measured footprints and every preservation validator remain.
Layout owns this coordination; Scene/adapters acquire no geometry policy.
No extra entry rule, schema, routing loop, project condition or copied preset.
