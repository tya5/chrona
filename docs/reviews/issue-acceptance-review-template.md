<!-- chrona:literal-acceptance/v1 -->

# Release Review — [Programme or Change]

Use this form for every review that supports closing one or more GitHub issues.
GitHub remains the mutable authority: copy every bullet under each issue's
`## Acceptance` heading verbatim at the observed revision.  Do not replace a
literal row with a programme-level restatement.

## Literal issue acceptance

### Issue #[number]

- Source: [Issue #[number]](https://github.com/tya5/chrona/issues/[number])
- Observed: YYYY-MM-DD

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | [Copied verbatim acceptance bullet] | met | [Evidence](relative-or-absolute-link) | — |

Allowed dispositions are `met`, `not met`, `narrowed`, and `deferred`.
`narrowed` and `deferred` require a successor issue or plan link.  An issue
with a `not met` row remains open.  Before closing an issue with a `narrowed`
or `deferred` row, post a GitHub closing comment that names the literal
criterion and links the same successor.

Repeat the complete issue subsection for every issue the review supports
closing.

## Programme-level criteria (optional)

Programme criteria may add cross-cutting evidence, but do not supply a
disposition for a missing literal issue row.

## Architecture conclusion

Record the responsible layers, boundary checks, and release disposition.
