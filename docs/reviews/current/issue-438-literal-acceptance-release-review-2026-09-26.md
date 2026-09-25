<!-- chrona:literal-acceptance/v1 -->

# Release Review — Literal Issue Acceptance and Close Disposition (#438)

## Literal issue acceptance

### Issue #438

- Source: [Issue #438](https://github.com/tya5/chrona/issues/438)
- Observed: 2026-09-26

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | The acceptance-review template or convention requires a verbatim row per acceptance bullet of each issue it closes. | met | [Template](../issue-acceptance-review-template.md) requires one copied row per acceptance bullet for every closed Issue; [checker tests](../../../tests/unit/tools/test_check_issue_acceptance_reviews.py) prove the marked form requires issue subsections, rows, and separate programme criteria. | — |
| 2 | No issue is closed with an unmet or narrowed criterion unless its closing comment says so and points at the follow-up. | met | [Template](../issue-acceptance-review-template.md) keeps `not met` Issues open and requires a closing comment naming every `narrowed` or `deferred` literal criterion with its successor.  [Checker](../../../tools/check_issue_acceptance_reviews.py) requires a linked successor for those dispositions. | — |

## Programme-level criteria (optional)

The structural checker deliberately does not fetch or claim to synchronize
mutable GitHub prose.  It validates only the local review contract, while the
issue URL and observed date make the human comparison auditable.

## Architecture conclusion

GitHub remains the authority for issue text and public close comments.
Repository review documents are immutable evidence.  The template defines the
human obligation; the standalone static checker verifies its finite local
shape and is run once by conformance.  No runtime, renderer, or materializer
layer participates.  #438 is accepted.
