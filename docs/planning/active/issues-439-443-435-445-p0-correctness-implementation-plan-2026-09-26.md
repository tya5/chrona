# Implementation Plan — P0 Public-Output Correctness (#439, #443, #435, #445)

**Programme design:**
`issue-454-p0-p1-p2-remediation-architecture-design-2026-09-26.md`.
**Architecture review:**
`issue-454-p0-p1-p2-remediation-architecture-review-2026-09-26.md`.
**Paint-order correction:**
`issue-454-p0-paint-order-adapter-correction-2026-09-26.md` and its review.

## Preconditions

- #400/#449 visible-fit completion is the only fit fallback; P0 must not
  restore refusal, clipping, or target-local wrapping.
- #439 and #443 publish atomically.  Revealing axis labels without first
  reserving rotated lanes and checking all tiers would release a newly visible
  overlap.
- Every source slice begins with `origin/main` comparison and publishes
  serially.  Generated corpus evidence is updated only after its corresponding
  source closure is complete.

## I454-P0-1 — Typed host-relative paint order (#439, #443 prerequisite)

**Files:** completed Layout placement model/composer, Scene model and
serialization/schema, v0.5 Scene builder, renderer ordering tests, focused
Layout/Scene fixtures.

1. Add a finite placement paint stratum and optional validated host placement
   identity to completed Layout text/shape records.
2. Complete background axis decoration, marks, hosted text, ordinary text, and
   annotation ordering in Layout.  Resolve stable numeric `paintOrder` there;
   retain semantic role → paint binding separately.
3. Validate host existence, same-surface ownership, and allowed semantic
   host/text pairs before Scene construction.
4. Thread the supplied order and host identity through Scene without a builder
   fallback.  Delete renderer-local mark-purpose visual grouping; every adapter
   serializes all visual primitive kinds in completed stable `(paintOrder,
   Scene input index)` order.  Keep interaction overlays separate and
   non-visual.

**Focused acceptance:** axis-band and mark-hosted text has a greater resolved
order than its host; invalid/missing/cross-surface host references fail;
ordinary text does not acquire an implicit host; SVG and each supported target
preserve supplied mixed-primitive order without a mark-purpose branch.

## I454-P0-2 — Atomic axis visibility and rotation closure (#439, #443)

**Files:** axis lane composition in Layout, surface composer collision setup,
axis fixtures, public Context/View resources, generated Scene/SVG evidence.

1. Compute each axis tier's required lane from transformed label bounds.
2. Allocate ordered lanes before label placement; use one shared axis-label
   collision domain across tiers.
3. Bind every axis label to its band host where present and give the band the
   declared background stratum.  Bind inside member labels and note-index
   badges to their completed mark host.
4. Regenerate all affected public materializers and inspect the formerly
   hidden axis, inside-label, and badge evidence.

**Focused acceptance:** every committed axis label has higher order than its
opaque band; every hosted inside label/badge has higher order than its host;
rotated `06-flight-readiness` labels reserve their lane and do not intersect
another axis tier; no unrelated text collision rule is weakened.

**Publication rule:** I454-P0-1 and I454-P0-2 source/evidence changes merge
as one atomic #439/#443 release unit.

## I454-P0-3 — Boolean table presentation (#435)

**Files:** View schema and typed contract, review-content normalization,
surface-content formatting, semantic registry/inventory if needed, HALCYON
Views, fixtures, generated evidence.

1. Introduce a closed boolean `presence` presentation with declared positive
   and negative display semantics; reject boolean sources lacking it.
2. Make formatting consume the typed presentation result rather than Python
   value stringification.  Keep role selection and text measurement upstream
   of Scene.
3. Migrate the three `missingActual` corpus Views to reader-meaningful text or
   existing declared icons, then regenerate affected materializers.

**Focused acceptance:** boolean text format is rejected at View ingress; both
presence states serialize deterministically; no committed Scene contains table
text `True` or `False`; the missing-observation realization evidence remains
reachable and interpretable.

## I454-P0-4 — Wrapped detail-panel completion (#445)

**Files:** detail/source measurement, Layout surface composition, completed
panel/text placement types, Scene tests, Controller-Z Japanese and affected
corpus resources/evidence.

1. Turn group detail and milestone digest content into measured multiline
   Layout blocks constrained by their own slot inline extent.
2. Allocate their panel block extent from wrapped lines and declared spacing.
   Complete an expanded canvas and typed warning if the requested block extent
   cannot contain the panel; do not permit adjacent-slot overprint.
3. Preserve selected metric, family, weight, baseline, lines, and source
   identity in each completed placement; Scene only projects them.
4. Regenerate affected public materializers and inspect the Japanese
   side-panel/digest slide.

**Focused acceptance:** CJK group details wrap at deterministic permitted
boundaries; group detail and digest bounds do not intersect each other; their
completed lines lie inside their allocated panels or carry an explicit
#449-compatible visible-overflow record; adapters do not break lines.

## I454-P0-5 — P0 release gate and #446 baseline

Run the P0 focused suites, all affected public materializers, generated Scene
and SVG diff review, diagnostic/value/schema inventories, and relevant
structural gates.  Run no redundant local full suite; use the three-OS CI full
pytest/conformance/wheel/smoke run and the newest-Python public materializer
job as release evidence.

Before beginning #446, run its proposed Scene evaluator against the completed
corpus.  P0 findings must be zero without a numeric blanket allowlist; any
explicit intentional host overlap must be explained by the typed host relation.
Publish an English P0 acceptance review mapping every literal issue acceptance
bullet before closing #439, #443, #435, or #445.
