# ADR-0022: Use a Product-Oriented Repository Layout

- **Status:** Accepted
- **Date:** 2026-09-20
- **Decision owners:** Repository architecture and packaging

## Context

Chrona began as a design artifact set named `timeline-design`. Product implementation,
tests, examples, schemas, conformance runners, and extensive delivery evidence were then
added around that artifact. The resulting repository obscures product entry points:

- public schemas and executable fixtures are nested under documentation;
- approximately fifty Python modules occupy one package level;
- Controller Z resources occupy the `examples/` root without a project boundary;
- tests are flat and mix unit, integration, conformance, and acceptance concerns;
- runtime code locates schemas and presets through repository-relative paths, which is
  incompatible with an installed wheel;
- completed plans and reviews dominate the active documentation surface.

## Decision

Adopt the root and package topology specified by Specification 32.

Chrona will use product-oriented root directories (`docs`, `schemas`, `conformance`,
`examples`, `src`, `tests`, `tools`). Python implementation will be grouped by semantic
owner. Unit tests will mirror source packages. Examples will be grouped first by project
and then by presentation variant or slide. Completed delivery evidence will be archived
without replacing the living specification.

The CLI is the only currently documented stable programmatic entry point. Because the
package is `0.1.0a0` and has no declared Python API, internal module paths may move in
this remediation. We will not preserve the flat layout through dozens of indefinite
facade modules. Deliberate public exports can be introduced separately.

Runtime resources will be packaged and loaded with `importlib.resources`. Public schema
source files remain discoverable at repository root and are included in distributions
without creating a second maintained authority.

## Alternatives considered

### Keep `timeline-design/` as an embedded artifact

Rejected. It preserves provenance at the cost of presenting an obsolete project
boundary as the current product boundary.

### Move documentation and examples but retain a flat Python package

Rejected. Fifty peer modules and a 1,281-line Scene builder already obscure ownership,
increase naming pressure, and prevent tests from mirroring architecture.

### Place tests beside production modules

Rejected for Python distribution hygiene. Mirrored `tests/unit/chrona/` paths provide
the same locality without packaging tests into the runtime artifact.

### Preserve every former module path with permanent facades

Rejected. No stable Python API was declared, and permanent facades would retain the
very flat topology being removed. Release-note migration guidance is sufficient for the
alpha version.

## Consequences

- Documentation and README links must be mechanically rewritten and checked.
- Schema and fixture consumers must stop depending on repository-relative paths.
- Tests and scripts require import/path updates.
- Git history will show a large number of renames, so moves and behavioral refactors are
  separated into different commits.
- The result is installable, discoverable, and aligned with the architecture described
  by the specification.

