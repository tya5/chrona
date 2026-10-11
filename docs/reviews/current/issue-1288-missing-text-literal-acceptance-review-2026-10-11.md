<!-- chrona:literal-acceptance/v1 -->

# Acceptance review — author-chosen missing text for table columns (#1288)

Implementation: [#1326](https://github.com/tya5/chrona/pull/1326) (merge `b1c4c60e7`), checked against `origin/main` `f890cea6c`. A table column's `missing` and each `missingBy` state (`inProgress`, `dueUnobserved`, `notYetDue`, `unavailable`) may be `{text: <1 to 8 characters, no control character>}` besides the enum spellings; a state not named keeps the column's `missing`; `affixes.missing` keeps wrapping whatever the absent text is in every absent state (Spec 06). `view-v0.28` is widened in place (enum to `oneOf`, five L1 expected-delta lines, Spec 56 section 3.2). Plan: [Status comment](https://github.com/tya5/chrona/issues/1288).

## Literal issue acceptance

### Issue #1288

- Source: [Issue #1288](https://github.com/tya5/chrona/issues/1288) (body, assignment and Status comments; no row was added after the body)
- Observed: 2026-10-11

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | For a column with `missingBy: {inProgress: {text: "?"}, dueUnobserved: blank, notYetDue: blank}` the Scene has a `?` text only in cells whose observation state is `inProgress`, and no text in the other blank cells. | met | [`test_missing_text_literal.py`](../../../tests/integration/test_missing_text_literal.py): `test_a_literal_for_one_state_shows_only_in_the_cells_of_that_state` renders four work packages through the packaged `executive-light` bundle and reads the Scene table-cell primitives of the column: `{done: "+4d", running: "?", overdue: "", later: ""}`. Companion tests: a literal `missing` is the default of the states not named, and the `missing` affix wraps the literal in every absent state (`"?!"`, `"!"`, `"!"`). Empty, nine-character, newline, empty-object and extra-key literals are rejected. All pass on `f890cea6c`. The test asserts text only, not the column text role the issue's scope mentions. Code: `contracts/resources.py`, `model/surface_content.py` `display_value`, `review/v05_content.py`; schema [`view-v0.28`](../../../schemas/view-v0.28.schema.yaml) `missingText`. In the committed corpus, [slide 25](../../../examples/halcyon-1/views/25-sunday.yaml) now declares the object form and its [SVG](../../../examples/halcyon-1/generated/25-sunday.svg) carries `?` twice. | — |
| 2 | Existing enum spellings are byte-identical. Synthetic fixture test. | met | The synthetic fixture is the test file above. Byte identity rests on two things, neither a before/after byte comparison inside a test: the pre-existing [`test_missing_by.py`](../../../tests/integration/test_missing_by.py) was not edited and passes (4 tests), and `test_the_enum_spellings_are_unchanged` pins `—` and blank cells to literal expected strings. The PR's measured count table reports 0 slides, 0 primitives and 0 diagnostics changed across the corpus ([PR body](https://github.com/tya5/chrona/pull/1326)). That is adequate here because the only code path added is the object branch; I did not re-render the corpus on the base commit. | — |
| 3 | Do not edit `examples/**`. | met | [Diff of #1326](https://github.com/tya5/chrona/pull/1326/files): schema, expected deltas, Spec 06, three source files and the test; no `examples/**` and no bot-generated file. | — |

## Programme-level criteria (optional)

CI on the merge: [full-matrix run 38067256833](https://github.com/tya5/chrona/actions/runs/38067256833) (workflow_dispatch on `5f2f056b2`, a descendant of the merge; macOS, Ubuntu and Windows `success`, which includes `conformance/run_conformance.py`, `pytest -n 4` and the wheel steps). Rows 1 to 3 are met; the reviewer's slide 25 adoption (named in the body) has already landed. The issue can close once this review lands. #1269 is the Sunday Strip programme this serves and stays with the reviewer.
