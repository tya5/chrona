<!-- chrona:literal-acceptance/v1 -->

# Literal acceptance review — #1681

Observed on `main` at `0c8179740`, which contains [PR #1688](https://github.com/tya5/chrona/pull/1688) (merge `4242d8ab`) and the derived-sync bot commit after it. Tests were run on this base in a private venv (`PYTHONPATH=src:.`, no install into a shared environment): `pytest tests/integration/test_finish_delta_label_packing.py` 2 passed. `tools/regenerate_public_examples.py --check` printed `Public materializers: PASS (50 slides)` and left the working tree clean. The PNG below was rendered here and opened.

Delivering PRs:

| Issue | Developer PRs | Reviewer PRs |
| --- | --- | --- |
| #1681 | [#1688](https://github.com/tya5/chrona/pull/1688) (finish-delta labels join their title's label packing; Spec [33](../../specification/33-intent-oriented-layout.md) and [38](../../specification/38-review-row-composition.md)) | none |

## Literal issue acceptance

### Issue #1681

- Source: [Issue #1681 body](https://github.com/tya5/chrona/issues/1681) (re-fetched 2026-10-18, three rows under "Acceptance")
- Observed: 2026-10-18

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | A synthetic key-row with forecast deltas on adjacent milestones: no text intersection, and every milestone stays labelled (#1501 row 1). | met | [`test_key_row_forecast_deltas_on_adjacent_milestones_never_meet_a_title`](../../../tests/integration/test_finish_delta_label_packing.py): a synthetic key-row View (`rows.points: key-row`, three milestones a working day apart, compact 14 px marks, 900 px viewport, forecast). It asserts that all three titles (`member-label:key-row:gate`, `-2`, `-3`) are drawn, that all three deltas (`+…*`) are drawn, and that no pair among the six texts overlaps by more than 1 px² (tolerance is stated in the test; the PR reports the pre-fix overlap as 507 px²). The test fails on the pre-fix code and passes here. Rule: [Spec 33](../../specification/33-intent-oriented-layout.md) (finish-delta label is a member of its title's packing, key-row extent holds delta and gap, key-row lane at least label height) and [Spec 38](../../specification/38-review-row-composition.md). Trial-5 look re-rendered here from `reviewer/trial-5-inputs` (`9fa6062de`, `looks/tbk` + `plan/project.yaml` + actual + baseline, `--forecast`, 1600 px) on current main: no `W_SCENE_TEXT_INTERSECTION` (the issue observed 4), and all five milestones (Kickoff, Design freeze, Beta release, Feature complete, Public launch) are labelled, see [trial-5-key-row-forecast-deltas.png](assets-1681/trial-5-key-row-forecast-deltas.png). Limits, judged and recorded, none of which breaks the literal wording: (a) placement quality, not intersection: in the PR's own trial render "Feature complete" lands one lane below its mark on the start side because the end side is held by Beta's deadline mark; it is drawn, labelled, and intersects nothing. In my render at 1600 px, "Public launch" is likewise drawn on the start side, left of its mark. (b) `W_LAYOUT_LABEL_OVERFLOW` for "Public launch" at the plot edge remains in the PR's render (visible-overflow, no overlap); it did not appear in my 1600 px render. It is an overflow warning, not text intersection, and the label is drawn. (c) The key row is 6 px taller (3 lanes of 18 px instead of 16 px) by design, Spec 38. (d) Rendering the trial inputs on current main needed two local edits that do not touch layout: `risk` declared on `checkpoint` and `colorEncoding` dropped from the `tbk` view, because the trial plan predates strict profile-field validation (#344, `E_PROFILE_FIELD_UNKNOWN`). The PNG is therefore the key-row look, not a pixel match of the trial image. | — |
| 2 | In ordinary rows, the delta and the title are separated by the declared gap, on a synthetic case. | met | [`test_ordinary_row_delta_and_title_keep_the_label_gap`](../../../tests/integration/test_finish_delta_label_packing.py): a synthetic forecast case; for each of the two rows the test measures the mark-to-delta gap (declared, asserted positive) and requires the delta-to-title gap to be at least that (`title_gap >= declared_gap`). The PR reports it failing on the pre-fix code (title on the wrong side, gap -32) and passing here; it passed in this review's run. The same PNG shows the ordinary rows with a visible gap after the delta (`+1d User research`, `+2d UX flows`, `+5d* Visual design system`), where the issue observed `+1dUser research`. Limit: the assertion is a lower bound (`>=`), as the criterion is "the declared gap"; the text in the PNG at 1600 px shows a small but present gap. | — |
| 3 | A count table of the public example changes and the PNGs. | met | The count table is in the [PR #1688 body](https://github.com/tya5/chrona/pull/1688): public examples 0 routes, 0 labels, 0 primitives, 0 new diagnostics (0 SVG, 0 Scene changed, 50 slides); trial-5 key-row and ordinary-row effects listed separately and marked not public. Re-measured here on `0c8179740`: `regenerate_public_examples.py --check` PASS (50 slides), no `examples/` change. PNGs: the PR's before/after images were kept local only (`/private/tmp/claude-501/fix1681-evidence/`), so they were not resolvable from the repository; this review adds the re-rendered after image, [trial-5-key-row-forecast-deltas.png](assets-1681/trial-5-key-row-forecast-deltas.png) (about 175 KB), as the resolvable record. A before image is not committed; the before state is recorded by the failing-on-main test results and the issue's own links. | — |

## Programme-level criteria (optional)

Issue #1681 has no programme-level criteria beyond the three rows above. It applies the label-packing rule of #1501 (row 1) to forecast finish deltas.

## Public side effects, re-measured

| Surface | Routes | Labels | Primitives | Diagnostics |
| --- | ---: | ---: | ---: | ---: |
| #1688: public examples (0 of 50 slides; 0 SVG, 0 Scene) | 0 | 0 | 0 | 0 |
| This review (docs and one PNG under `docs/reviews/`) | 0 | 0 | 0 | 0 |

## Architecture conclusion

A finish-delta label is now part of the same packing as its title: key-row extents include the delta and gap, key-row lanes are at least label height, and a title beside a delta is measured from the delta. All three rows are met literally. The recorded limits (one-lane start-side fallback for "Feature complete", edge overflow warning for "Public launch" in the trial render, 6 px taller key row) concern placement quality and are not part of the issue's wording, so they do not narrow row 1. If the reviewer wants labels kept on their own lane or no edge overflow, that is a new criterion and needs its own issue; none was filed here.
