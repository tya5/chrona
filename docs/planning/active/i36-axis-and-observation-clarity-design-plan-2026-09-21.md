# Issue 36 Design Plan

**Issue:** #36
**Status:** Active

## Objective

Correct axis granularity selection at clipped window edges, place missing-actual indicators at their planned marks, and make dependency connectors legible without adding presentation policy to Project or renderer adapters.

## Design steps

1. Audit the Axis, View comparison facets, Scene primitive roles, and Theme token boundaries.
2. Specify fitting against natural bucket width while retaining clipped rendering geometry.
3. Specify missing-actual eligibility and planned-mark anchoring.
4. Specify dependency token ownership and contrast-safe example bindings.
5. Review cross-boundary consistency and publish the completed design.

## Exit criteria

- no authored coordinates or project-specific branches;
- View owns whether missing actual is requested;
- Scene owns geometry; Theme owns connector color;
- clipped edge buckets cannot force a coarser axis level; and
- each decision has diagnostics and testable acceptance criteria.
