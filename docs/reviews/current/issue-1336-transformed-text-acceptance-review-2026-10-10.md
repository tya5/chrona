<!-- chrona:literal-acceptance/v1 -->

# Issue #1336 — transformed text bounds

Authority: [current design, architecture and implementation plan](https://github.com/tya5/chrona/issues/1336#issuecomment-6094661552).
Implementation `3a257021`; integrated ready main
`48957a0cb9064d2ff76a42c21241843dc8383a5c`
([trusted gate](https://github.com/tya5/chrona/actions/runs/38041136428)).
Published WIP: `wip/issue-1336-transformed-text`.
Feature PR: [#1339](https://github.com/tya5/chrona/pull/1339).
Corpus attribution is verified; final-head checks and exact-main release remain required.

## Literal issue acceptance

### Issue #1336

- Source: [Issue #1336](https://github.com/tya5/chrona/issues/1336)
- Observed: 2026-10-10

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | In a Scene test, a group header with `textTransform: uppercase` has text bounds equal to the measured width of the transformed string. With `groupHeaderBand: text`, the band ends at the drawn text end plus nothing. | met | [Synthetic Scene/SVG tests](../../../tests/integration/test_transformed_group_header_bounds.py) compare plain and role-marked uppercase text with independently already-painted source text at identical compression/spacing; assert exact band endpoint and SVG bounds, including bounded ellipsis. The new group/caller batch passes ten tests (4.52s). | — |
| 2 | Existing examples change only where a transformed role was mismeasured. List those slides in the PR. | met | [Exact-base artifact receipt](https://github.com/tya5/chrona/issues/1336#issuecomment-6096225763): 12 Scenes / 145 transformed Text bounds corrected; all 46 SVGs identical. Full Scene JSON is identical after replacing those bounds. PR #1339 lists every affected slide. No corpus output is manually edited. | — |
| 3 | Do not edit `examples/**`; the reviewer adopts `groupHeaderBand: text` in Sunday after this lands. | met | Owned product change is one [shared Layout measurement argument](../../../src/chrona/presentation/layout/text.py); tests use synthetic declarations. Sunday adoption remains the reviewer's work. | — |

## Programme-level criteria (optional)

Scope audit: plain/role-marked group headers, axis labels, table headers/cells,
legend, slot headings and kind bars share `place_text`. Their earlier natural
measurement and ellipsis already apply the role's transform; final placement
discarded it for ordinary case transforms. One shared correction restores the
existing Specs07/50 contract without schema, Theme or adapter changes.

Focused coverage: **235 unique passing tests**, including asymmetric casing,
compression, spacing, rotation, multiline and small caps. Before correction,
the asymmetric batch has 48 failures / 24 passes; text plus small caps then
passes 88 tests (8.87s). Source identity and run payload remain intact;
compression is applied exactly once.
[Six caller-specific tests](../../../tests/integration/test_transformed_text_placement_sites.py)
share one synthetic render, observe actual native composers and assert each
axis/table-header/table-cell/legend/slot-heading/kind-bar placement and Scene
transport against its painted width. Each case uses source text with demonstrably
different casing-dependent advances; the synthetic axis uses short-month labels.
Replaying the baseline ordinary-text measurement causes **six independent
assertion failures (1.92s)**, not a shared fixture error; restoring the correction
passes all six. Existing group/row/table/slot-heading regressions pass 135 tests
(137.81s), with two unrelated existing Pillow deprecation warnings.

An additional no-transform regression replays the previous source-case
measurement argument with every role explicitly untransformed and compares
serialized Scene and SVG bytes: one pass (1.60s). A transformed/compressed
legend-grid regression checks labels and start-column caption reservations.
Latest source integration `503268a1` adopts #1279: **45 transformed-text/grid/
viewport/transport tests pass (17.28s)**. Its generated-only ready delta needs
no duplicate focused run.

Exact corpus audit on `dc2fe027785743b1ecd58dc02752ace9b36583a9` against the
ready base above: run [38041670817](https://github.com/tya5/chrona/actions/runs/38041670817),
artifact 11665907574. Root and Luna independently verify all 101 base blobs,
zero additions/retirements, 34 unchanged Scenes and 46 unchanged raw SVGs.
The 12 changed Scenes contain only 145 corrected transformed Text bounds;
no text, font settings, primitive membership, route, diagnostic, canvas or
viewport changes. The generated contrast report reflects corrected text
sample coordinates; the living receipt records its exact attribution.

Closure requires a fresh snapshot and successful checks on the final PR head,
then three-OS release CI on the exact published main containing this review.
The linked receipt records final provenance without metadata-only commits.
