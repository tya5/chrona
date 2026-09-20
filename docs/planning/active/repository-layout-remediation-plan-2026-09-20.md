# Repository Layout Remediation Plan — 2026-09-20

**Status:** Design complete; implementation authorized only after this design phase is
validated and published.  
**Normative design:** Specification 32 and ADR-0022.

## Implementation status

| Phase | Status | Published commit |
|---|---|---|
| Design | Complete | `7823848` |
| R1 — Root documentation and contracts | Complete | `e3ef808` |
| R2 — User examples | Complete | `171b0cd` |
| R3 — Test topology | Complete | `e4b24b1` |
| R4 — Source package relocation | In verification | — |
| R5 — Presentation module decomposition | Pending | — |
| R6 — Packaging and OSS closure | Pending | — |

## 1. Objective

Convert the legacy artifact-oriented repository into the product-oriented layout in
Specification 32 without changing Chrona semantics, deterministic output, or accepted
feature scope.

One phase equals one verified commit published to GitHub `main`. No later phase may be
accumulated locally before the preceding phase is published. If implementation exposes
a missing ownership or compatibility decision, stop that implementation, complete and
publish the design correction, then resume.

## 2. Baseline

- `timeline-design/` contains the living specification, schemas, conformance fixtures,
  executable validators, and historical evidence.
- `src/chrona/` has approximately 50 flat modules; `presentation_scene.py` is the
  largest at approximately 1,281 lines.
- `tests/` has approximately 47 flat test modules.
- `examples/` combines one organized ASTER project with approximately 30 flat
  Controller Z resources.
- production modules resolve schemas and presets through repository-relative paths.
- baseline acceptance is 251 pytest tests plus complete Chrona conformance.

## 3. Migration map

### Phase R1 — Root documentation and contracts

| Current | Target |
|---|---|
| `docs/specification/` | `docs/specification/` |
| `docs/decisions/` | `docs/decisions/` |
| `docs/research/federation/` | `docs/research/federation/` |
| active planning records | `docs/planning/active/` |
| completed planning records | `docs/archive/planning/` |
| current acceptance reviews | `docs/reviews/current/` |
| completed point-in-time reviews | `docs/archive/reviews/` |
| `docs/traceability/` | `docs/traceability/` |
| documentation assets | `docs/assets/` |
| `schemas/` | `schemas/` |
| `conformance/` | `conformance/` |
| `docs/manifest.json` | `docs/manifest.json` |
| `conformance/validation.json` | `conformance/validation.json` |

The duplicate legacy `timeline-design/docs/examples/federation/` tree is removed after
confirming that the maintained conformance fixtures supersede it. Root README, workflow,
schemas, manifests, validators, and every textual path reference are updated together.

Acceptance: all links/path references resolve, pytest and conformance pass, and the
published commit contains no semantic code change.

### Phase R2 — User examples

Move ASTER and Controller Z into the project/variant structure from Specification 32.
Add `examples/README.md` and project READMEs with exact reproduction commands. Update
manifests, scripts, tests, README images, and all design evidence paths. Do not alter
source YAML meaning or renderer behavior.

Acceptance: byte-identical regenerated SVGs, PNG raster verification where applicable,
all example acceptance tests, full pytest, and conformance.

### Phase R3 — Test topology

Classify existing tests without changing assertions:

- one-module behavior → `tests/unit/chrona/<owned-package>/`;
- cross-module/profile behavior → `tests/integration/`;
- command-line behavior → `tests/cli/`;
- checked-in example reproduction → `tests/acceptance/examples/`.

Update pytest configuration and test-relative resource lookup. Conformance fixtures
remain in `conformance/` and are not copied.

Acceptance: collected test count cannot decrease; test IDs may move but assertions and
coverage responsibilities remain; full pytest and conformance pass.

### Phase R4 — Source package relocation

Create the package boundaries from Specification 32 and move modules mechanically.
Update relative imports, scripts, tests, and the CLI entry point. Do not split functions
or change algorithms in this phase. Add explicit package `__init__.py` files with small,
intentional exports.

Acceptance: no import references a former flat module, CLI commands behave identically,
pytest and conformance pass, and the built wheel imports successfully.

### Phase R5 — Presentation module decomposition

Split `presentation_scene.py`, `gantt_surface.py`, and `review_svg.py` according to the
model/layout/scene/renderers/review boundaries. Move code without changing semantic
owners. Add focused mirrored unit tests before reducing the legacy modules; remove the
legacy modules when all callers use the owned locations.

Acceptance: deterministic examples remain byte-identical, the complete test count does
not decrease, full conformance passes, and no package cycle violates Specification 32.

### Phase R6 — Packaging and OSS closure

- package schemas and runtime resources;
- replace repository-root lookup with `importlib.resources`;
- add isolated wheel-install smoke tests;
- move maintainer scripts to `tools/` and update commands;
- add `LICENSE`, `CONTRIBUTING.md`, `SECURITY.md`, and `CHANGELOG.md`;
- add Issue and pull-request templates;
- set GitHub checkout depth sufficient for revision-bound conformance;
- remove `timeline-design/`, obsolete paths, stale status files, and temporary shims.

License selection is a user/legal policy decision. Until selected, R6 may add the
contribution/security/changelog structure but MUST NOT invent a license. Final OSS
closure remains explicitly blocked only on that selection; repository restructuring is
otherwise complete.

Acceptance: all ten invariants in Specification 32, clean checkout, wheel smoke test,
full pytest, full conformance on both local and GitHub CI, and a final acceptance review.

## 4. Verification matrix

Every phase runs:

1. `git diff --check`;
2. full `pytest`;
3. `conformance/run_conformance.py` (or the pre-R1 legacy path for the design-only phase);
4. path/reference search for former locations introduced by that phase;
5. exact published-tree verification after GitHub update.

R2 also runs SVG reproduction and raster review. R4–R6 build a wheel. R6 installs that
wheel outside the repository and exercises validation, scheduling, settings resolution,
and CLI discovery.

## 5. Rollback and publication

Moves use Git-aware renames where possible. Each phase begins at published `main` and
has no dependency on unpublished work. GitHub updates are serial and non-forced. A phase
that fails acceptance is not published and later phases do not start.
