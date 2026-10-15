<!-- chrona:literal-acceptance/v1 -->

# Issue #1568 — coarse annotation search

Release acceptance requires the publication's exact-main three-OS gate.

## Literal issue acceptance

### Issue #1568

- Source: [Issue #1568](https://github.com/tya5/chrona/issues/1568)
- Observed: 2026-10-16

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | A synthetic crowded-near-anchor fixture with free space far away places the note without overlap. | met | [Integration fixtures](../../../tests/integration/test_annotation_coarse_search.py) verify a far-space fit and that every fine candidate precedes coarse retries; [search tests](../../../tests/unit/chrona/presentation/layout/test_annotation_search.py) cover finite budgets, degenerate regions, positive strict routed tails, joint connector rejection and unchanged as-of safety.24 focused tests pass. | — |
| 2 | The Sunday roadmap reproduction draws no overlap (viewed as PNG). | deferred | Superseded by the [approved successor](https://github.com/tya5/chrona/issues/1568#issuecomment-6202905637): only217.47px before as-of, versus234.79/241.49px bodies; the204.25px body's remaining legal origins are all blocked. [Faithful PNG and feasibility evidence](https://github.com/tya5/chrona/issues/1568#issuecomment-6197487540). No input tuning or junction exemption. | [#1581](https://github.com/tya5/chrona/issues/1581) |
| 3 | All public SVG and Scene files are byte-identical. The time cost is reported. | not met | Full public-snapshot comparison remains required. [Published profile](https://github.com/tya5/chrona/issues/1568#issuecomment-6195293083): three in-plot contexts1.55/1.48/1.75s before,1.60/1.49/1.72s after; bounded by existing position and connector-state budgets. Faithful infeasible Sunday3.61→3.79s, PNG/Scene unchanged. | — |

## Programme-level criteria (optional)

The [reviewer disposition](https://github.com/tya5/chrona/issues/1568#issuecomment-6202905637)
authorizes closure on rows1/3, with row2 explicitly superseded by #1581.

## Architecture conclusion

Layout alone retries completed box/connector pairs against the existing
obstacle inventory. All fine candidates precede bounded coarse candidates;
successful fine placements and the anchor-side safety contract are unchanged.
Scene/adapters receive completed geometry. No schema, new knob, corpus edits,
shared-endpoint exemption or as-of crossing belongs to this issue.
