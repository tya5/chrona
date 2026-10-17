<!-- chrona:literal-acceptance/v1 -->

# Issue #1627 — label and route recovery acceptance

Candidate code `73add45e5`, point-proposal test `143ad2fee`, based on ready
main `56a86557cda64aea4def668ff847dcd93135caa8`. Retained-text design
`a0b2506ad` was published before the correction code.
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
| 3 | Public SVG/Scene changes listed with counts. | met | [Batch evidence and status](https://github.com/tya5/chrona/issues/1627#issuecomment-6230332335): repository derived-workflow snapshot at `73add45e5` against `56a86557c`; per-slide counts below. Official final-head CI must confirm them before merge. | — |

## Public-output batch

50 SVG and 50 Scene pairs compared; 92 files are byte-identical. Only
`halcyon-1/16-gallery-editorial-lanes` changes visually. Its 238 primitives
retain all identities; none are added or removed. No primitive array reorders.

| Slide | Changed routes | Changed member labels | Changed primitives total | Added / removed | New / removed diagnostic codes |
| --- | ---: | ---: | ---: | --- | --- |
| 16-gallery-editorial-lanes | 8 + 1 halo | 6 | 15 | 0 / 0 | 0 / 0 |
| Every other slide (49) | 0 | 0 | 0 | 0 / 0 | 0 / 0 |

Slide16 SVG has 14 changed elements (eight routes, six labels). Scenes02/04/
11/12/19 change routing-receipt payloads only; Scene03 only reorders identical
keyed `laneObstacles`. Slide04 has one fewer `I_LAYOUT_RELATION_ROUTING`
diagnostic; no diagnostic code is introduced or removed on any slide.
The contrast report changes six label coordinates, with no ratio/severity
change; inventory changes are 32 source-line references. The changed public
SVG was viewed as before/after PNGs. No examples or generated outputs are
PR-authored. Exact trial3 project-only PNGs were rerun after the correction;
all three retain 22 names/31 logical relations and pass the row2 geometry checks.
The ready-main wallboard legend-overflow warning is unchanged by this fix
([separate disposition](https://github.com/tya5/chrona/issues/1649#issuecomment-6232738521)).

## Programme-level criteria (optional)

210 focused cases pass across two batches and the point-test expectation
rerun; 38 documentation/ledger checks and the literal-review validator pass.
All 125 CLI characterization cases pass after fixture `7722c10a6`: the default
HALCYON render now suppresses one member name rather than four (one variance
warning remains), and its recovery receipt is 8 fallback/16 settled instead of
7/17. Only that expected stdout changes; CLI envelopes/file controls stay exact.
CI39024533939 failed this stale fixture alone; derived-ready cascaded that
failure. All other pytest shards, conformance and public reproduction passed.
Require exact-head PR checks and three-OS full
pytest/conformance/wheel plus public reproduction on exact main containing this
review; keep issue1627 open until complete.

## Architecture conclusion

Spec50 owns the revised on-demand preference: initially suppressed optional
names only, one existing retry, fewest distinct logical route owners then
declared rank. Admission checks the completed visible-text inventory without
replacing preceding eligibility/ranking; retry revalidates visible requests first.
Full measured footprints and every preservation validator remain. Optional-name
coverage need not reproduce the retired visible preferred-rung repair; neutral
count tests prove member-only suppression accounting and zero omission.
Layout owns this coordination; Scene/adapters acquire no geometry policy.
No extra entry rule, schema, routing loop, project condition or copied preset.
