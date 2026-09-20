# Repository Layout Design Review — 2026-09-20

**Disposition:** Pass — implementation may begin after the design commit is published.

## Scope reviewed

- current root, source, test, example, schema, fixture, and documentation topology;
- internal Python dependency direction;
- repository-relative runtime resource lookup;
- current example reproduction and conformance entry points;
- documentation authority and historical evidence retention;
- phase isolation, validation, publication, and rollback.

## Findings closed by the design

1. The obsolete `timeline-design` product boundary is replaced by explicit root owners.
2. Schemas and conformance fixtures are no longer presented as documentation.
3. Python source and unit tests share mirrored responsibility boundaries.
4. Controller Z and ASTER inputs, variants, and derived artifacts gain explicit project
   ownership without duplicating semantic facts.
5. Installed-wheel resource lookup becomes a release invariant.
6. Presentation file decomposition preserves the established Layout/Scene/adapter
   ownership rather than introducing a new model.
7. Completed plans and reviews remain available but no longer obscure the current spec.
8. Large moves are separated from behavioral/module decomposition to retain reviewable
   diffs and deterministic rollback.

## Residual constraint

No license may be chosen implicitly. The absence of a license does not prevent the
structural migration, but public reuse remains prohibited until the owner selects one.

## Authorization

The plan is complete enough for phased implementation. Any newly discovered semantic
choice, public-API promise, schema ownership conflict, or example-data duplication must
return to design and be published before implementation resumes.

