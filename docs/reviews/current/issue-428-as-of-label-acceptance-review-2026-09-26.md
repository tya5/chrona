<!-- chrona:literal-acceptance/v1 -->

# Release Review — As-of Label Content and Label Chips (#428)

**Reviewed product:** `17e5e1a2` on `main`, preceded by the design correction `43b3cf14`. **Design:** [design](../../design/issue-428-as-of-label-design-2026-09-26.md), [correction](../../design/issue-428-as-of-label-correction-2026-09-26.md), [architecture review](issue-428-as-of-label-architecture-review-2026-09-26.md), Specification 39 (as-of label content and label chips).

**Slicing:** the plan had two code slices, I428-1 (View v0.23) and I428-2 (chips). They landed as one commit, because the chip example (`label: Today`) needs v0.23's bare label, and the evidence regeneration of both touches the same slides. This review therefore also serves as both slice reviews.

## Evidence and byte review

- **View v0.23:**
  - `schemas/view-v0.23.schema.yaml` adds an optional `markers[].date: {form: localized-date, nameTable?}`;
  - v0.22 is `transitioning` in the schema inventory;
  - every shipped View, preset View and fixture migrated;
  - the 12 Views with an `asOf` marker declare `date: {form: localized-date}`, except `02-programme-board` (`label: Today`).
- **Label text:** [`test_as_of_label_is_the_declared_text_and_a_date_only_in_a_declared_form`](../../../tests/unit/chrona/presentation/review/test_v05_content.py) covers:
  - `Today` → `Today`;
  - a declared form → `as of Aug 20, 2027` (en-US) and `as of 2027/08/20` (ja-JP, or via `nameTable`);
  - no marker → `As of Aug 20, 2027`.
- **Chips:** [`test_label_chips.py`](../../../tests/integration/test_label_chips.py) covers:
  - the committed `02` chip bounds equal the text bounds plus padding, with a pill radius, painted under the text;
  - a member-label chip is produced from a Theme role alone, with no as-of code path;
  - themes without a chip role draw none.
- **Public evidence:** all 22 regenerated, then `--check` PASS.
  - Every slide with an as-of label changes its text from the ISO date to the localized form, for example `As of 2026-05-20` → `As of May 20, 2026`, with the width following.
  - The four wallboard slides (`02`, `04`, `07`, `11`) gain `chip:as-of-label`, whose top is aligned to the timeline top.
  - No other primitive geometry changed.
- **Perceptibility:** `04` first failed `E_SCENE_TEXT_INTERSECTION`, because the chipped label fell back above the plot. Fixed by the anchor rule in the correction, not by suppressing the check. The gate passes.
- **Checks:** full `pytest` 1187 passed, 20 skipped (plus the new chip tests); conformance PASS.
- **Visual check:** a PNG crop of `02-programme-board` shows `Today` in a rounded chip on the dashed as-of line.

## Literal issue acceptance

### Issue #428

- Source: [Issue #428](https://github.com/tya5/chrona/issues/428)
- Observed: 2026-09-26

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | `as_of_label: Today` renders as `Today`, with no date appended. | met | [Label unit test](../../../tests/unit/chrona/presentation/review/test_v05_content.py); committed `02-programme-board` as-of text `Today`. | — |
| 2 | A document that wants a date with the label states the form it wants, in the vocabulary axis labels already use. | met | View v0.23 `markers[].date: {form: localized-date, nameTable?}`, formatted by the axis name table; [label unit test](../../../tests/unit/chrona/presentation/review/test_v05_content.py). | — |
| 3 | A label can carry a background sized from its own measured text, and the mechanism is not specific to the as-of marker. | met | Registered chip bindings for as-of, member and finish-delta labels; [member-label chip test](../../../tests/integration/test_label_chips.py). | — |
| 4 | One committed example renders an as-of label as a bare word in a filled chip, and reproduces byte-identically. | met | [`02-programme-board`](../../../examples/halcyon-1/manifest.yaml) with `Today` in `chip:as-of-label`; [committed chip test](../../../tests/integration/test_label_chips.py); materializer `--check`. | — |

## Programme-level criteria (optional)

- CI: [four-job CI run 36250349082](https://github.com/tya5/chrona/actions/runs/36250349082) on `06740ce2`, green.
- Not taken: the issue's proposal item 4 (a declared candidate ladder) is outside the literal acceptance and belongs to #466's placement model.

## Architecture conclusion

- View owns the label text and the date form.
- The axis name table formats the date.
- The registry owns the chip semantics; Layout owns chip geometry and footprint.
- Scene projects a Rect, and contrast treats it as ground. The adapters are unchanged.

Release disposition: all rows met.
