# Implementation Plan — Literal Issue Acceptance and Close Disposition (#438)

## I438-1 — Review contract

Add a Markdown template and a focused structural checker.  For every issue
closed by a review, require its URL, observed date, ordered literal criterion
text, finite disposition (`met`, `not met`, `narrowed`, or `deferred`),
evidence, and successor link for `narrowed`/`deferred`.  Add valid and invalid
fixtures.

## I438-2 — Adoption evidence

Apply the template to the next issue-specific release review.  The review must
show that programme criteria are separate from literal issue acceptance.

## I438-3 — Publication gate

Run focused template/checker tests, documentation link checks, conformance,
and the existing CI matrix.  Confirm no runtime or generated-materializer
artifact changes.  A future issue is closed only after its GitHub close comment
records every literal row whose disposition is not `met`, with its successor
link where required.
