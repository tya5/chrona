# Issue 119 — Resource Schema Diagnostics Design Plan

## Objective

Make closure ingress reject every supported presentation resource against its
declared schema before downstream consumers read it, with a stable resource
kind diagnostic and JSON-pointer source reference for the first schema error.

## Questions to resolve

1. Confirm the current contract parser's schema coverage and identify where
   `ContractError` loses the schema error path at the closure boundary.
2. Define one diagnostic representation that preserves the resource kind,
   stable code, and RFC 6901-style pointer without exposing YAML parser state.
3. Verify that context, referenced resources, optional resources, snapshots,
   and profile packages use the same boundary rather than ad-hoc validation.
4. Specify negative cases for View, Theme, Color Scheme, Actual set, Summary
   profile, and existing resource kinds.

## Architectural constraints

- Schema validation remains in contracts/closure ingress; neither Layout,
  Scene, renderer, nor use case may validate raw YAML.
- Contracts are constructed only after validation and remain immutable.
- Resource references and identity checks remain separate from schema shape
  diagnostics.
- The solution must not add renderer- or target-specific policy.

## Deliverables

An English design review, an independently reviewable implementation plan, and
one implementation PR with focused negative tests and full closure regression
coverage.
