# Repository Layout Final Acceptance — 2026-09-20

**Decision:** Accepted with one explicit external policy dependency: license selection.

## Published phase evidence

| Phase | Evidence |
|---|---|
| Design | `7823848` |
| R1 — Root documentation and contracts | `e3ef808` |
| R2 — User examples | `171b0cd` |
| R3 — Test topology | `e4b24b1` |
| Design verifier correction | `194c73f` |
| R4 — Source package relocation | `f52a145` |
| R5 — Presentation decomposition | `7a8b311` |
| R6 — Packaging and OSS closure | `47b88ec` |
| Design resource-authority correction | `714b3a7` |
| R6A — Runtime resource authority correction | `3141bbc` |
| R6A CI — Editable source resource discovery | this phase commit |

Every published update was non-forced and its Git tree was checked against the local
index before publication.

## Acceptance results

- 253 pytest tests pass; resource tests cover schema resolution and package-owned data.
- Complete Chrona conformance passes.
- Controller Z and ASTER deterministic acceptance artifacts remain reproducible.
- The wheel contains the runtime schemas, built-in presentation settings, and both
  content-addressed font-metrics tables.
- The installed wheel validates and schedules a project, resolves built-in settings,
  and discovers CLI help from outside the checkout.
- GitHub Actions now checks out full history and repeats pytest, conformance, wheel
  build, installation, and out-of-checkout smoke validation.
- `git diff --check` passes and no obsolete `timeline-design/`, flat source module,
  flat presentation test, `scripts/`, or root checkpoint file remains tracked.
- Runtime modules use `importlib.resources`; no runtime schema or preset depends on
  walking from `__file__` to the repository root.
- Hatch dev mode exposes both `src/` and the root schema package, so editable installs
  resolve the same sole schema authority from any working directory.

The two existing `jsonschema.RefResolver` deprecation warnings remain accepted
technical debt. They do not change the pass result and should be migrated to the
`referencing` API in a separate behavior-preserving maintenance change.

## Invariant review

All ten invariants in Specification 32 are satisfied for the implemented repository
structure, packaging, examples, tests, documentation, and serial publication history.
The public `schemas/` package is the sole tracked schema authority and is force-included
only while building the wheel. Presets and font metrics have one tracked authority under
`src/chrona/resources/`; conformance validates that packaged authority directly.

## Remaining policy dependency

No `LICENSE` file is present because the maintainer has not selected a license.
Chrona must not be represented as licensed for reuse until that decision is made.
This does not block the repository restructuring, but it is the only remaining
open-source release-policy blocker.
