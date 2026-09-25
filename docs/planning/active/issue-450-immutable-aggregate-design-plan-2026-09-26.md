# Design-Correction Plan — Immutable Aggregate Diagnostics (#450)

## Question

Clarify whether a direct immutable Context resolver may retain the historical
single `ClosureError` when its one invalid resource contains several schema
violations.

## Decision work

1. Reconcile the literal #450 requirement (every violation; every known
   resource) with the existing one-error compatibility acceptance.
2. Review the Context → closure → CLI exception transport so aggregate output
   does not become a second rendering/validation path.
3. Amend I450-3b and update characterization tests before publication.
