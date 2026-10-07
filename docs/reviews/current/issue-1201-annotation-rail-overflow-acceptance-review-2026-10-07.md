<!-- chrona:literal-acceptance/v1 -->

# Release Review — completed annotation rail overflow

Implementation evidence: `f14efa50e1ded01b9da0d9ee13bbe5064cc6d12c`, [PR #1203](https://github.com/tya5/chrona/pull/1203); [design/architecture/implementation plan](https://github.com/tya5/chrona/issues/1201#issuecomment-6038602583).
Local focused tests: 98 passed; the public control rechecked after tying byte comparison to the authored size (3 passed). All required implementation [PR checks](https://github.com/tya5/chrona/actions/runs/37629626518) passed, including three pytest shards, conformance and reproduction. Shared artifact11485998690, SHA-2560751fd3568c5ebb9d06f4def8c08cb5041e20b0b50884ecb7ee7ae718fdaec11: 141 exact-baseff333f82 paths, no additions/retirements.

## Literal issue acceptance

### Issue #1201

- Source: [Issue #1201](https://github.com/tya5/chrona/issues/1201)
- Observed: 2026-10-07

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | A fixture with three kind-headed notes in a rail: as the heading size grows, the notes keep non-overlapping boxes up to the point where they exceed the rail. | met | [Synthetic15/17/20/22 SVG tests](https://github.com/tya5/chrona/blob/f14efa50e1ded01b9da0d9ee13bbe5064cc6d12c/tests/integration/test_annotation_rail_overflow.py): full-box separation, required child containment and cross-note bar/heading/body noncollision. | — |
| 2 | Beyond that point, a diagnostic is reported and nothing is raised. | met | [Unnumbered exhaustion and natural-width fixtures](https://github.com/tya5/chrona/blob/f14efa50e1ded01b9da0d9ee13bbe5064cc6d12c/tests/integration/test_annotation_rail_overflow.py): all three complete boxes retained, explicit W_LAYOUT_LABEL_OVERFLOW, no raise. | — |
| 3 | On Title Card, `size.annotation-heading: 22` renders without error. The reviewer then adopts 22 px. | narrowed | [Actual public-context15/17/22 SVG tests](https://github.com/tya5/chrona/blob/f14efa50e1ded01b9da0d9ee13bbe5064cc6d12c/tests/integration/test_titlecard_annotation_heading.py) pass with distinct frames and correct22px text. [Owner board](https://github.com/tya5/chrona/issues/454), observed above, explicitly assigns target adoption to the reviewer and excludes it from dev closure. | [Reviewer adoption #1182](https://github.com/tya5/chrona/issues/1182) |

## Programme-level criteria (optional)

Corpus: 65/66 SVG and Scene pairs byte-identical, including current TitleCard15px. Yuya's already-overwide TVAC note moves to a collision-free anchor-derived rail position: 17/422 primitives changed, zero added/removed; frame/text/stamp/artwork/leader move together, anchor/style/size and1600×900 canvas unchanged. Its kind header gains the existing overflow warning (4→5 warnings). Actual SVG boxes match Scene and all three frames remain separate. Diagnostic inventory is location-only; contrast report follows the moved note. No examples edits.
Architecture: ordinary candidates and numbered-list order unchanged; full natural fallback geometry, completed rail footprints and diagnosed overflow remain Layout-owned. Scene/adapters/schema and global overlap assertion are unchanged. Specs33/43/44 aligned; diff review found no unresolved structural issue.
Closure requires successful final PR checks, fresh ready-main publication and the three-OS pytest/conformance/wheel/materializer run on the exact published commit containing this review. The closing comment must cite that receipt; earlier implementation or PR CI is not a substitute.
