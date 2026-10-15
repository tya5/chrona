# #1373 row 1: table header typography (2026-10-15)

Baseline: `origin/main` 7a418e2db. Row 1 asked for a Theme role for column headers (size, weight, tracking, transform)
and, per the reviewer decision of 2026-10-15, no View member.

## Finding

That role already exists. `tableColumnLabel` (#991, PR #1015) is the column-header role: Layout measures and places every
header in it when the Theme declares it (column minimum, baseline, ellipsis follow its size, weight, letter spacing and
transform), Scene paints the header with its `fill`, and a Theme without it keeps `text`. The behaviour is specified in
`docs/specification/07-style-and-theme.md` (Table header role). The gap report row was stale.

## Decision

No second role (`table.header`) is added: it would duplicate `tableColumnLabel` and leave two names for one job.
No registry, schema or spec change.

## Slice

- Gap report row 1 marked resolved by #1015.
- Tests in `tests/integration/test_table_header_role.py` for the parts #1015 did not pin: weight and transform change the
  rendered header, the header cell width follows the upper-casing, a role equal to `text` changes nothing, and the Typst and
  TikZ adapters render a header with the role declared.
- Adoption: the default Editorial Theme does not declare `tableColumnLabel`. Declaring it is a reviewer step, outside this slice.
