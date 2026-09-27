<!-- chrona:literal-acceptance/v1 -->

# Release Review — Committed Capability Slides (#434)

**Reviewed product:** I434-1 `3a3d549b` (reports), I434-2 `a3edf7ab` (slides), and fixes `fb9edf53` (report refresh) and `5919646e` (a contrast-valid group-band fill, via a new Controller Z `capabilities-band` category) on `main`. **Design:** [design](../../design/issue-434-committed-capability-slides-design-2026-09-27.md), [architecture review](issue-434-committed-capability-slides-architecture-review-2026-09-27.md). This review also serves as both slice reviews.

## Evidence and byte review

- **New slide `controller-z/capabilities`** with its own View, Layout and Theme (copies of `executive` and `executive-light`):
  - `backgroundExtents.rowBand: both` with alternating rows;
  - `rowDistribution: fill`;
  - `grouping.presentation: band`, with group bands bound to a distinct category fill so they read against the stripes;
  - an `{fr: 1}` title column in a `{fr: 3}` table slot with `ellipsize-with-source`, followed by a `Finish` date column;
  - an uppercase, letter-spaced legend;
  - a `numeric` (Δ) role in Noto Sans Mono.
- **`controller-z/annotations`:** the callout leader takes its own dashed `textMuted` stroke. It is the only slide with leaders, and its only change is that leader's `paint.stroke` and `paint.dash`. The other Controller Z slides change provenance only.
- **Deviation during implementation:** an `{fr}` title column alone did not keep `Finish` fixed. The table slot was `minmax(min: content)`, and since #487 its minimum is the measured content, so the slot grew with the title. The capabilities Layout therefore sizes the table slot `{fr: 3}` with `ellipsize-with-source`. The allocation then fixes the date column, and a title that no longer fits is ellipsized rather than moving it.
- **Tests:** [`test_capability_slides.py`](../../../tests/integration/test_capability_slides.py) has one test per capability, read from the committed Scenes. The date-column test re-renders with a 54-character title and asserts `column:Finish` does not move. [`test_presentation_coverage.py`](../../../tests/unit/tools/test_presentation_coverage.py) and [`test_corpus_coverage.py`](../../../tests/unit/tools/test_corpus_coverage.py) cover the reports.
- **Test-helper correction:** `test_no_text_leaves_the_viewport` measured every SVG text with the Theme's *first* font family. With a monospace token first it mis-measured Noto Sans labels. It now keys metrics by each text's own family and weight.
- **Corpus counts:** 24 slides, 200 axis labels and 8 hosted DVT labels, updated deliberately.
- **Corrections after the first CI run:** the committed contrast report was stale, and it also carried 7 decoration contrast errors from the first group-band colour: orange was 1.087 against the canvas and 1.027 under the stripes, and a neutral grey failed the slip-delta text floor at 3.94. The final `#D8DDE6` band clears all three, and `presentation_contrast --check` is PASS.
- **Checks:** full `pytest` 1244 passed, 22 skipped; conformance PASS; PNG of the new slide inspected.

## Literal issue acceptance

### Issue #434

- Source: [Issue #434](https://github.com/tya5/chrona/issues/434)
- Observed: 2026-09-27

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | Each of the six capabilities is rendered by at least one committed slide that reproduces byte-identically. | met | Items 1–4 and the comment's letter spacing, text transform and mono face on [`controller-z/capabilities`](../../../examples/controller-z/manifest.yaml); item 5 on `orion-asic/gates`; item 6 on `controller-z/annotations`; [capability tests](../../../tests/integration/test_capability_slides.py); materializer `--check` of 24 slides. | — |
| 2 | No view, theme or layout under `examples/` is unreferenced, or each is listed with a reason. | met | [`tools/corpus_coverage.py`](../../../tools/corpus_coverage.py) reports unreferenced presentation files, each with a declared reason, and `--check` fails otherwise; [report](../../examples/corpus-coverage.md); [test](../../../tests/unit/tools/test_corpus_coverage.py). | — |
| 3 | `presentation-coverage.md` names the slide that realizes a non-default `every`. | met | [Non-default integer vocabulary](../../gallery/presentation-coverage.md): `view body.axis.tiers[].every = 2 → orion-asic/gates`; [test](../../../tests/unit/tools/test_presentation_coverage.py). | — |

## Programme-level criteria (optional)

- CI: [four-job CI run 36255206852](https://github.com/tya5/chrona/actions/runs/36255206852) on `2aa0debc`, green.

## Architecture conclusion

Corpus and derived-report work only; no presentation semantics changed. Release disposition: all rows met.
