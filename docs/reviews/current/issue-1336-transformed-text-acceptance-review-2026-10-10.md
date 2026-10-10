<!-- chrona:literal-acceptance/v1 -->

# Issue #1336 — transformed text bounds

Authority: [current design, architecture and implementation plan](https://github.com/tya5/chrona/issues/1336#issuecomment-6094661552).
Implementation `3a257021`; integrated ready main
`bf9313bbe19dd9a386f10bda98485f5e8d139c96`
([trusted gate](https://github.com/tya5/chrona/actions/runs/38033174047)).
Published WIP: `wip/issue-1336-transformed-text`.
No PR or public-artifact acceptance yet.

## Literal issue acceptance

### Issue #1336

- Source: [Issue #1336](https://github.com/tya5/chrona/issues/1336)
- Observed: 2026-10-10

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | In a Scene test, a group header with `textTransform: uppercase` has text bounds equal to the measured width of the transformed string. With `groupHeaderBand: text`, the band ends at the drawn text end plus nothing. | met | [Synthetic Scene/SVG tests](../../../tests/integration/test_transformed_group_header_bounds.py) compare plain and role-marked uppercase text with independently already-painted source text at identical compression/spacing; assert exact band endpoint and SVG bounds, including bounded ellipsis. The new group/caller batch passes ten tests (4.52s). | — |
| 2 | Existing examples change only where a transformed role was mismeasured. List those slides in the PR. | not met | [Current work plan](https://github.com/tya5/chrona/issues/1336#issuecomment-6094661552): fresh exact-base public snapshot, per-slide attribution and PR list remain required. No corpus output is manually edited. | — |
| 3 | Do not edit `examples/**`; the reviewer adopts `groupHeaderBand: text` in Sunday after this lands. | met | Owned product change is one [shared Layout measurement argument](../../../src/chrona/presentation/layout/text.py); tests use synthetic declarations. Sunday adoption remains the reviewer's work. | — |

## Programme-level criteria (optional)

Scope audit: plain/role-marked group headers, axis labels, table headers/cells,
legend, slot headings and kind bars share `place_text`. Their earlier natural
measurement and ellipsis already apply the role's transform; final placement
discarded it for ordinary case transforms. One shared correction restores the
existing Specs07/50 contract without schema, Theme or adapter changes.

Asymmetric upper/lowercase, compression, spacing, rotation and multiline
regressions: before correction, 48 fail / 24 pass; after correction, the full
text plus small-caps batch passes **88 tests (8.87s)**. Original source identity
and small-caps run payload remain intact; compression is applied exactly once.
[Six caller-specific tests](../../../tests/integration/test_transformed_text_placement_sites.py)
share one synthetic render, observe actual native composers and assert each
axis/table-header/table-cell/legend/slot-heading/kind-bar placement and Scene
transport against its painted width. Each case uses source text with demonstrably
different casing-dependent advances; the synthetic axis uses short-month labels.
Replaying the baseline ordinary-text measurement causes **six independent
assertion failures (1.92s)**, not a shared fixture error; restoring the correction
passes all six. These repeated regression checks are not counted as new tests.
Existing group/row/table/slot-heading regressions: **135 pass (137.81s)**;
two existing Pillow deprecation warnings remain unrelated. Across the three
non-overlapping batches, **233 tests pass**; the repeated fixture check is not
counted again. These focused checks do not substitute for public output or full
release evidence.

An additional no-transform regression replays the previous source-case
measurement argument with every role explicitly untransformed and compares
serialized Scene and SVG bytes: **one pass (1.60s)**. Total unique focused
coverage is **234 passing tests**; this synthetic identity proof does not
replace the pending public-artifact attribution.
After adopting #1289 source main on `0a3e96a8`, the combined group-header,
six-caller, small-caps and plain-zero integration batch passes **27 tests (16.94s)**.
The source-to-ready delta changes managed reports only; these are repeat
integration checks, not additional unique coverage.

Closure requires final focused/caller tests, current-base artifact attribution,
exact-head PR checks and successful three-OS release CI on the exact published
main containing this review.
