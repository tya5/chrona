# Implementation Plan — Packaged Monospace Metrics Catalog (#410)

**Design:** `issue-410-packaged-monospace-catalog-design-2026-09-26.md`.
**Architecture review:**
`issue-410-packaged-monospace-catalog-architecture-review-2026-09-26.md`.

## I410-4 — Closed catalog selection

Add immutable `FontMetricsCatalog` construction from a validated declared v3
descriptor.  Replace the one global Layout metric at every source and surface
measurement boundary with role-local exact selection.  Preserve one selected
metric in each completed placement and reject absent family/weight before Scene
projection.  Add focused selection, source/table/label measurement, and
structural no-global-metric-after-treatment tests.

**Acceptance:** a synthetic second face changes measured geometry only for its
selected role; unknown family/weight cannot reach Scene; no adapter interface
changes and ordinary one-face contexts remain materializable.

## I410-5 — Packaged face and public evidence

Import the licensed Noto Sans Mono Regular source and v3 metrics, retain its
OFL notice, and add it to every packaged default descriptor/Context closure.
Add a monospace Theme role to one HALCYON public Context and regenerate its
Scene/SVG plus target evidence atomically.  Include focused resource identity,
raster registration, Scene identity, and generated artifact assertions.

**Acceptance:** an installed wheel contains the face and metrics; the selected
public role measures and paints Noto Sans Mono; all public materializers remain
reproducible; regular Noto Sans output remains unchanged where no monospace
role is selected.

## I410-6 — Release gate

Run focused tests for both slices, public materializer reproduction, all
inventory/coverage/reachability/import-direction gates, conformance, generated
SVG/PNG diff review, full parallel pytest, wheel build/size/install smoke, and
one three-platform CI run.  Publish an English acceptance review mapping the
original #410 criteria to evidence.  Close #410 only after all gates pass.

## Publication discipline

Publish each slice serially after fetching `origin/main`, confirming the exact
ahead/behind range, and checking the intended diff.  A missing selection path,
resource ownership conflict, or target choosing a font returns to the design
review; do not add a compatibility fallback or adapter-local correction.
