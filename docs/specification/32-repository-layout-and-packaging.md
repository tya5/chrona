# Repository Layout and Packaging

**Status:** Design complete  
**Owns:** Repository topology, source-package boundaries, test topology, example layout,
runtime resources, and distribution invariants.

## 1. Purpose

Chrona is one product repository. Its layout MUST expose the product entry points before
historical delivery evidence, keep runtime data out of documentation, and make the
relationship between implementation, tests, conformance, and examples explicit.

The repository root is the only workspace root. The legacy `timeline-design/` wrapper
MUST be removed after its contents are assigned to their owning root directories.

## 2. Required root layout

The maintained root directories are:

| Path | Authority |
|---|---|
| `docs/` | Human-readable specification, architecture, decisions, plans, reviews, research, and historical evidence. |
| `schemas/` | Public machine-readable wire contracts. This is the single source-tree authority for schemas. |
| `conformance/` | Product conformance manifests, fixtures, and runners. |
| `examples/` | User-facing, runnable projects and their deterministic derived artifacts. |
| `src/chrona/` | Installable Python implementation. |
| `tests/` | Unit, integration, CLI, and example-acceptance tests. |
| `tools/` | Maintainer utilities that are not product entry points. |

Root files own project discovery and contribution policy: `README.md`, `LICENSE`,
`CHANGELOG.md`, `CONTRIBUTING.md`, `SECURITY.md`, and `pyproject.toml`.

## 3. Documentation topology

`docs/` contains:

- `specification/`: the current normative specification and supplemental rules;
- `architecture/`: implementation-facing architecture and dependency maps;
- `decisions/`: ADRs; an ADR records rationale but never overrides the current spec;
- `planning/active/`: work that is not yet accepted;
- `reviews/current/`: current acceptance and release evidence;
- `research/`: non-normative investigations;
- `archive/planning/` and `archive/reviews/`: completed point-in-time evidence;
- `assets/`: documentation-only assets.

There MUST be one navigable `docs/README.md`. Completed plans and reviews MAY be moved
to the archive only after their disposition is reflected in the living specification,
status ledger, or current review. Git history is not a substitute for the current
normative specification.

## 4. Runtime and public data

Schemas are product contracts, not documentation. Their sole source authority is the
importable resource package at `schemas/`. Hatch MUST force-include that directory at
`chrona/resources/schemas/` when building a wheel. The generated wheel paths MUST NOT be
tracked as a second source-tree copy. Runtime code MUST load the source package or the
wheel-installed package through `importlib.resources`; runtime modules MUST NOT derive
the repository root from `__file__`.

Built-in presets and content-addressed font metric tables are runtime resources. Their
source authority is `src/chrona/resources/`. Documentation may link to those resources
and conformance may validate them but MUST NOT own a duplicate. Tests MUST install the
built wheel into an isolated environment and prove schema, preset, and font-metric
lookup without a repository tree.

## 5. Python package boundaries

The final package boundaries are:

| Package | Responsibility | Initial module allocation |
|---|---|---|
| `chrona.core` | Diagnostics, Date-only temporal semantics, project validation. | `diagnostics`, `temporal`, `validation` |
| `chrona.scheduling` | Date/DateTime scheduling, capacity, and cost observations. | `scheduler`, `temporal_datetime`, `datetime_scheduler`, `datetime_migration`, `capacity`, `cost_observations` |
| `chrona.storage` | Revision stores, snapshots, and project loading. | `revision_store`, `snapshots`, `loader` |
| `chrona.commands` | Typed project, Actual, View, AI, gesture, and editor commands. | `commands`, `actual_commands`, `view_commands`, `ai_proposals`, `gestures`, `editor` |
| `chrona.extensions` | Profiles, registries, and package lifecycle. | `profiles`, `extension_registry`, `package_lifecycle` |
| `chrona.collaboration` | Merge/audit and federation. | `collaboration`, `federation` |
| `chrona.presentation` | Actual intake, closure, settings, Layout, Scene, surfaces, and SVG output. | all presentation/render/review modules |
| `chrona.release` | Output capability, release packages, and successor release. | `output`, `release_package`, `successor_release` |
| `chrona.app` | CLI and interactive application orchestration. | `cli`, `interactive`, `review` |

Dependencies MUST point toward semantic owners. `core` cannot import presentation,
application, release, or adapters. Scheduling may depend on core. Presentation may
consume core/scheduling results. Application code may orchestrate all public services.

The documented stable entry point remains the `chrona` CLI. No stable Python module API
has been declared for the alpha release. Repository-internal imports and tests therefore
move to the owned packages without retaining dozens of top-level compatibility modules.
`chrona.__init__` MUST expose only deliberately selected public symbols.

## 6. Presentation decomposition

Moving files and changing behavior MUST be separate phases. After package relocation,
the oversized presentation modules are decomposed into:

- `presentation/model/`: projection and surface-content input;
- `presentation/layout/`: constraint solving, axes, labels, lanes, and routing;
- `presentation/scene/`: primitive model, marks, annotations, paint resolution, and
  deterministic Scene construction;
- `presentation/renderers/`: generic SVG serialization and table-timeline surface;
- `presentation/review/`: Plan/Actual projection, summary, and detail orchestration.

The existing semantic ownership from Specifications 27–31 remains unchanged. A module
split MUST NOT introduce renderer-owned scheduling, paint, measurement, or routing.

## 7. Test topology

Unit tests mirror source packages below `tests/unit/chrona/`. Cross-package workflows
belong in `tests/integration/`; CLI behavior belongs in `tests/cli/`; deterministic
example reproduction and visual-contract assertions belong in
`tests/acceptance/examples/`.

Conformance is not an ordinary unit-test directory. `conformance/` remains independently
executable and owns normative fixtures. Tests MAY invoke conformance but MUST NOT copy
its fixtures. Repository tests that need a conformance fixture MUST use a read-only,
repository-relative locator; conformance fixtures are neither test-package resources nor
runtime package resources.

Every implementation module with independent behavior SHOULD have a corresponding unit
test path. This rule does not require artificial one-test-file-per-data-class splits.

## 8. Example topology

Each user-facing project owns one directory and a README. Shared source facts are stored
once per project; presentations are nested by variant or slide:

```text
examples/controller-z/
  project.yaml
  actual.yaml
  shared/
  variants/<variant>/{settings.yaml, expected.svg, preview.png?}

examples/aster-ssd/
  project.yaml
  actual.yaml
  shared/
  slides/<slide>/{view.yaml, settings.yaml, expected.svg, preview.png?}
```

Shared source resources are stored once at project scope. A variant or slide owns a
`view.yaml` only when its selection differs from its siblings. Controller Z therefore
uses its shared project view, while the ASTER slides own distinct per-slide views.

Derived artifacts MUST be reproducible and named `expected.svg`, `preview.png`, or
`gallery.html` so source and output cannot be confused. No sample-specific behavior may
be added to product Python code.

## 9. Maintainer tools and generated files

Maintainer-only scripts move to `tools/`. User-supported operations SHOULD be CLI
commands. Python cache, pytest cache, local environments, build output, and transient
raster output MUST remain ignored and untracked.

## 10. Acceptance invariants

The restructuring is complete only when:

1. no tracked path remains below `timeline-design/`;
2. no production module reads `timeline-design/docs` or derives a repository root for
   runtime resources;
3. all internal imports use the new owned packages;
4. source and unit-test paths mirror each other by responsibility;
5. each example has a README and deterministic reproduction test;
6. the complete pytest and conformance suites pass;
7. a built wheel passes an isolated smoke test;
8. documentation links and declared fixture paths resolve;
9. GitHub Actions fetches sufficient history for revision-bound conformance;
10. each migration phase is a separately verified and published commit.
