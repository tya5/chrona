# Implementation Plan — Cross-Python Public Evidence Reproduction (#442)

**Status:** approved for implementation.
**Design:** `issue-442-cross-python-reproduction-2026-09-25.md`.
**Architecture review:**
`issue-442-cross-python-reproduction-architecture-review-2026-09-25.md`.

## I442-1 — Deterministic Layout arithmetic

**Files:** `layout/model.py`, `layout/presentation.py`, `layout/routing.py`,
`layout/dependency_network.py`, `layout/sources.py`, `layout/surface_composer.py`,
and focused unit tests.

1. Add float-only `geometry_sum` at the Layout numeric boundary, using
   `math.fsum` without rounding.
2. Replace every audited float geometry `sum` that contributes to allocation,
   bounds, ports, advances, routing, or fit.  Retain explicit Decimal and
   integer/count sums.
3. Add a regression with the historical six-column allocation inputs that
   proves the completed coordinates equal the `fsum` result rather than the
   version-dependent builtin result.

**Acceptance:** focused Layout tests pass; Decimal/count behavior remains
covered; no visible-policy change is introduced.

## I442-2 — Closed structural policy

**Files:** a dedicated tool and unit test under `tools/` and `tests/unit/tools/`.

1. Encode the audited float/Decimal/count classification in an AST structural
   check.
2. Reject direct builtin float placement sums in reviewed Layout modules.
3. Make a fixture prove an unclassified float sum is rejected and approved
   Decimal/count patterns remain accepted.

**Acceptance:** the check passes live source, fails the negative fixture, and
is invoked by conformance.

## I442-3 — Evidence and dual-minor release gate

**Files:** all generated public artifacts affected by deterministic arithmetic,
`.github/workflows/conformance.yml`, relevant integration/CI tests, generated
diagnostic/coverage reports where applicable.

1. Regenerate the complete public corpus once after I442-1 and review Scene
   and SVG diffs.
2. Preserve existing cross-platform Python 3.11 conformance; add an Ubuntu
   Python 3.12 job that runs the complete public corpus materializer
   reproduction test.
3. Run the materializer evidence suite, full pytest suite, conformance,
   structural tools, and local public CLI reproduction.  Verify 3.11 where
   available; CI is the authoritative 3.11/3.12 matrix evidence.

**Acceptance:** all corpus evidence reproduces on both minors in CI; the
current red README-command gate turns green; no interpreter identity enters
Scene provenance.

## Publication boundary

I442-1 and I442-2 may be reviewed independently but are not released with
partial generated evidence.  The #412 v0.5 migration changes the immutable
inputs of that same corpus, so I442-3 publishes the source, structural gate,
workflow, regenerated corpus, and acceptance review **together with** #412's
approved contract, geometry, adapter, and corpus changes as one fast-forward
release.  The release is atomic for evidence, while the issue ownership and
acceptance criteria remain separately reviewed.
