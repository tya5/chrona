# Architecture Review — P1-I1 Contract Correction (#404, #403, #388, #389, #409)

**Decision:** Accepted.  This correction is required before P1-I1 implementation resumes.

| Boundary | Review result |
| --- | --- |
| View / Layout | Pass.  The corrected width forms reuse the established logical-size vocabulary without admitting Layout Profile's physical-size choices into View. |
| View / Scene | Pass.  `rowDecoration` selects finite facts only; it carries neither bounds nor paint order.  I3 remains responsible for completed placements. |
| Project / View | Pass.  The hierarchy invariant uses View nesting intent, not WBS strings or a claim that explicit rows alter Project hierarchy. |
| Dependency network | Pass.  Table-only declarations are excluded, preserving a surface-specific View boundary rather than silently ignoring them. |
| Migration | Pass.  A clean v0.16 migration with no v0.15 ingress keeps one accepted contract and prevents a compatibility normalizer from concealing the changed authoring requirement. |

The initial object-only width spelling would have created a second size
language at the same boundary that the primary review required to remain
shared.  Omitting row decoration would have deferred author intent into I3.
The corrected contract removes both ambiguities.  Allocation cardinality and
all geometry remain Layout invariants and are not moved into the parser.
