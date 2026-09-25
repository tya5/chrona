# Design Plan — Literal Issue Acceptance and Close Disposition (#438)

## Problem

Release reviews currently choose their own acceptance tables.  A literal issue
criterion can disappear during restatement and an issue can close without its
disposition being visible at its public source of truth.

## Questions

1. How does a review preserve the issue's acceptance bullets verbatim without
   making the repository attempt to mirror mutable GitHub issue text?
2. Which finite dispositions express completion honestly?
3. What belongs in a reusable review template, a release review, and the
   GitHub close comment respectively?
4. How can the convention be structurally checked without claiming that an
   automated parser has verified arbitrary GitHub prose?

## Deliverables

- English design and whole-architecture review.
- An implementation plan for a review template, an acceptance-matrix fixture,
  and structural checks.
- A documented close-comment convention for non-`met` rows.
