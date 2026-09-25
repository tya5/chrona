# Design — Literal Issue Acceptance and Close Disposition (#438)

## Decision

Every acceptance review that supports closing one or more issues begins with
a **literal acceptance matrix for each issue**.  The author copies each bullet
under that issue's `## Acceptance` heading verbatim into one ordered row; no
paraphrase can replace it.  Each row has exactly one disposition:

| Disposition | Meaning | Closing rule |
| --- | --- | --- |
| `met` | The literal criterion is satisfied with linked evidence. | The issue may close. |
| `not met` | The criterion is currently false. | The issue remains open. |
| `narrowed` | A reviewed successor deliberately reduces the criterion. | The issue close comment names the literal criterion and links its successor. |
| `deferred` | Work is intentionally moved to a tracked successor. | The issue close comment names the literal criterion and links its successor. |

Programme-level criteria may follow the literal matrix, but are explicitly
additive.  They cannot provide a disposition for a missing literal row.

## Boundaries

GitHub issue text remains the authoritative mutable source.  The repository
review is a dated evidence record, not a synchronization cache.  Reviewers
must record the issue URL, observed issue revision/date, and copied bullets;
automation checks the review document's required structure and finite
disposition vocabulary only.  It does not pretend to prove that remote text
has not changed after review.

The release review owns evidence and disposition.  The GitHub closing comment
owns public discoverability: any `narrowed` or `deferred` row is repeated there
with the successor issue/plan link.  No rendering, schema, closure, or CI
runtime behavior changes.
