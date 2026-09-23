# Issues 259, 278, and 279 Implementation Plan

## Preconditions

The completed design and architecture review is merged as `f128ddf`.  No
implementation slice starts until this plan is merged.  Every slice is a
separate branch and PR; before each merge, fetch `origin/main`, inspect the
proposed range and PR checks, merge without force, then verify the resulting
GitHub merge commit.

## I259 — contributor render-dependency contract

**Files:** `README.md`, `CONTRIBUTING.md`, relevant contributor-install and
wheel/materializer tests if an expectation is missing.

**Change:** make `.[dev,render]` the documented environment for the documented
full test command.  Do not change runtime dependencies or make `render` an
implicit library install.

**Acceptance:** a fresh `.venv` using the exact published commands runs
`python -m pytest`; documentation and CI agree; focused documentation/packaging
tests and the full suite pass.

## I279-A — typed rounded-geometry foundation

**Files:** `presentation/layout/surface_quality.py`, new focused path-geometry
module if warranted, `presentation/scene/model.py`, metric resolution in
`presentation/layout/sources.py`, `usecases/render_review.py`, and focused unit
tests.

**Change:** add optional non-negative Theme metrics and typed completed mark
corner treatment/path commands.  Preserve absent/zero byte behavior, clamp
radii in Layout, and validate completed path commands and port preservation.

**Acceptance:** metric type/default/zero/negative tests; span, diamond, and
route geometry tests; Scene receives but does not calculate completed values;
full suite passes.  No example Theme opts in yet.

## I279-B — renderer and public-evidence rollout

**Files:** `v05_builder.py`, SVG/Typst/TikZ renderers, renderer tests, Theme
fixtures, selected HALCYON Theme(s), generated public SVG evidence and its
characterization tests.

**Change:** project the typed foundation into semantic mark primitives only;
serialize rounded span, rounded diamond, and rounded relation path in every
supported target or fail explicitly for an unavailable target capability.
Opt in one public Theme deliberately, regenerate only its affected evidence,
and prove bands/shading/legend/annotation rectangles remain square.

**Acceptance:** target-specific positive and zero tests; public materializer
checks and generated-SVG diff review; all HALCYON contexts remain materializable;
focused and full tests pass.

## I278-A — automatic policy and projection

**Files:** `schemas/view-v0.9.schema.yaml`, contract resource parsing,
`model/projection.py`, View/projection tests.

**Change:** add automatic `points` policy, default `own-row`, typed
`FoldedPointProjection`, deterministic predecessor eligibility, and stable
diagnostics.  Establish group-header preconditions and keep folded header
points outside `ReviewRowProjection` table subjects.

**Acceptance:** schema and typed-boundary tests; all policy outcomes,
deterministic duplicate-relation handling, comparison variants, and unchanged
own-row projection test; full suite passes.

## I278-B — layout, Scene, and materialization rollout

**Files:** review-content composition, row/header placement helpers,
surface composer, scene projection, fixtures, HALCYON View/context, generated
SVG evidence, and focused acceptance tests.

**Change:** allocate header tracks from GroupPlacement extents; emit completed
marks, labels, ports, relations, and annotations for header targets; omit their
table cells.  Add a representative HALCYON automatic-header fold only after
the generic behavior is covered.

**Acceptance:** no blank point table rows; visible collision-managed titles;
correct relation and annotation endpoints; expected row-budget reduction;
materializer and SVG evidence checks; focused tests and full suite pass.

## Per-slice review gate

Review the diff for responsibility drift before publishing: Project/Scheduler
must not learn presentation policy; View must not learn coordinates; Layout
must remain the only geometry and route owner; Scene must remain a projection;
and renderers must not introduce semantic or geometric fallback.  Any contrary
finding stops the slice and requires a published design correction before code
resumes.
