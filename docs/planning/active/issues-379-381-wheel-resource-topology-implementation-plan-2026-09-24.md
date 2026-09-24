# Implementation Plan: Wheel Resource Topology and Evidence (#379, #381)

**Status:** Proposed

**Implements:** [Wheel resource topology design](../../design/issues-379-381-wheel-resource-topology-design-2026-09-24.md)

## I379-1 — Single-authority init template

Add the Hatch force-include mapping for `examples/halcyon-1`.  Introduce the
resource-layer template resolver and make local init consume it.  Remove the
duplicated package template, its synchronization checker, and the conformance
entry.  Add source-mode tests that prove the resolver can copy an initialized,
materializable project without direct path coupling.

**Files:** `pyproject.toml`, `src/chrona/resources/__init__.py`,
`src/chrona/usecases/local_authoring.py`,
`src/chrona/resources/examples/**` (delete),
`tools/check_init_template.py` (delete), `conformance/run_conformance.py`,
and focused tests.

**Acceptance:** one source template remains; source init works; unsupported
templates and non-overwrite behavior retain their current diagnostics.

## I381-1 — Installed-wheel smoke matrix

Extend `tools/wheel_smoke.py` with public icon-catalog and Draft PNG journeys.
Assert the copied catalog's contract header/non-empty payload and PNG signature.
Make the initialized temporary project the only fixture source for wheel smoke;
do not add direct private-resource assertions.

**Files:** `tools/wheel_smoke.py`, focused smoke/unit tests where needed.

**Acceptance:** an installed wheel opens icon catalog bytes and declared font
bytes; removing either required wheel resource makes the public journey fail.

## I379-2/I381-2 — Packaging and release gate

Build and inspect wheel members, run source and isolated-wheel init/smoke,
focused tests, conformance without the obsolete sync gate, structural checks,
public materializer byte checks, full parallel pytest, generated SVG review,
and three-platform CI.  Publish a release review before closing both issues.

**Acceptance:** the explicit resource matrix, source/wheel separation, and
all architecture-review boundaries have direct test or release evidence.
