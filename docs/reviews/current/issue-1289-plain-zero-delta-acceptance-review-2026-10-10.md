<!-- chrona:literal-acceptance/v1 -->

# Acceptance review — plain zero for signed table columns (#1289)

Implementation: [#1328](https://github.com/tya5/chrona/pull/1328) (merge `f0c1a6fa`), checked against `origin/main` `289444de`. A signed column (`signedNumber` or `signedDays`) takes an optional `zero` property, `signed` (default) or `plain`: `plain` draws a zero value without a sign (`0`, `0d`), non-zero values keep their sign, and an `onTime` affix still wraps the text. `zero` on a column whose format is not signed is `E_VIEW_COLUMN_ZERO`. `view-v0.28` gains the optional property in place (Spec 56 section 3.2, schema equivalence `additive`); Specification 46 states the rule. Plan: [Status comment](https://github.com/tya5/chrona/issues/1289).

## Literal issue acceptance

### Issue #1289

- Source: [Issue #1289](https://github.com/tya5/chrona/issues/1289) (body, assignment, Status and merge-coordination comments)
- Observed: 2026-10-10

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | With `zero: plain`, a zero delta cell text is `0` (`0d` for days) and non-zero values keep their sign; the default output is byte-identical. | met | [`test_plain_zero_delta.py`](../../../tests/integration/test_plain_zero_delta.py): `test_plain_zero_draws_zero_without_a_sign_and_keeps_every_other_sign` (`0`; late and early cells equal the default), `test_plain_zero_for_days_is_zero_d` (`0d`, `+…d`, `-…`), `test_an_on_time_affix_still_wraps_the_plain_zero` (`0*`), `test_the_default_keeps_the_sign_at_zero` (`+0`) and `test_an_explicit_signed_zero_is_the_default_output` (explicit `signed` equals absent). Code: `contracts/resources.py` (`TableColumn.zero`, `E_VIEW_COLUMN_ZERO` at the usability check), `model/surface_content.py` `display_value`, `review/v05_content.py`; schema `schemas/view-v0.28.schema.yaml` `zero`; rule in Specification 46. Byte identity of the corpus: no View under `examples/**` declares `zero` (search on `289444de`), and the [PR count table](https://github.com/tya5/chrona/pull/1328) reports 0 slides, 0 primitives and 0 diagnostics changed. | — |
| 2 | Synthetic fixture test covering negative, zero and positive values. | met | The same [test file](../../../tests/integration/test_plain_zero_delta.py) builds one synthetic table with an early (negative), on-time (zero) and late (positive) cell (`_cells`, keys `early`, `ontime`, `late`) and all seven tests pass on `289444de`; it also refuses `zero` on a text column (`E_VIEW_COLUMN_ZERO`) and an unknown spelling (schema error). | — |
| 3 | Do not edit `examples/**`. | met | [Diff](https://github.com/tya5/chrona/pull/1328/files): Spec 46, `view-v0.28` schema, three source files and the test only; no `examples/**` and no bot-generated file. | — |
| 4 | The reviewer adopts it in slide 25. | deferred | Reviewer step, not a developer closing condition: the [slide 25 view](../../../examples/halcyon-1/views/25-sunday.yaml) does not yet declare `zero: plain` (search on `289444de`). Owner note: adoption is the reviewer's change under the Sunday Strip programme and does not need a code change here. | [#1269](https://github.com/tya5/chrona/issues/1269): assemble the Sunday Strip target; adoption of this property in slide 25. |

## Programme-level criteria (optional)

None. Rows 1 to 3 are met; row 4 is the reviewer's adoption step on #1269. The issue can close after this review and the three-OS run on the `main` commit that publishes it are cited, unless the owner wants adoption confirmed first.
