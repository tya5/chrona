<!-- chrona:literal-acceptance/v1 -->

# Release review — artwork container padding from the inner edge

Implementation: [#1221](https://github.com/tya5/chrona/pull/1221) (`24c93edf`), plan in the [Status comment](https://github.com/tya5/chrona/issues/1216#issuecomment-6049346421). Only `theme_tokens.annotation_container`, the Theme schema artwork rule (S0 `schema_equivalence --base-rev origin/main` PASS with two expected-delta entries) and Spec 07 change; Layout reads the same content insets. Count table: 0 slides, routes, labels or primitives changed (`tools/regenerate_public_examples.py --check` PASS, 67 slides). Mutation check: dropping the slice term fails three tests.

## Literal issue acceptance

### Issue #1216

- Source: [Issue #1216](https://github.com/tya5/chrona/issues/1216)
- Observed: 2026-10-08

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | Swapping the artwork glyph keeps the declared padding from its inner edge. | met | [test_artwork_padding.py](https://github.com/tya5/chrona/blob/24c93edfcdf7ee3c1142bb604a81b74800274e20/tests/integration/test_artwork_padding.py): the padding form renders byte-equal to the computed absolute inset for two different sliceInsets, and the text keeps slice inset x unit + padding from the box edge on every side after the swap; exclusion with `contentInsetEm`, missing artwork and a balloon are `E_THEME_TOKEN_TYPE`. Spec 07. | — |
| 2 | Absent declarations give byte-identical output. | met | No bundled Theme or example declares `contentPaddingEm`: `regenerate_public_examples.py --check` PASS (67 slides, 0 changed) and the green [PR checks](https://github.com/tya5/chrona/pull/1221). | — |

## Programme-level criteria (optional)

Adopting `contentPaddingEm` in Yuya's scroll Theme is the reviewer's step, not a dev closing condition.
