# Implementation Plan: Portable Icon Catalogs and Immutable Visual Assets (#350)

**Status:** Complete for the narrow v0.1 foundation; superseded as #350 product
completion by `issue-350-icon-ecosystem-redesign-design-plan-2026-09-23.md`.
**Implements:** Design Plan #350 (including its 2026-09-23 amendment),
Specification 64, and UC-33
**Design review:** `docs/reviews/current/issue-350-portable-icon-catalogs-architecture-review-2026-09-23.md`

## Scope and release claim

The completed slice accepts user-authored local SVG and PNG icon files through a pinned
`icon-catalog`, uses them as an explicitly View-bound leading label icon and mark, and
materializes them reproducibly. SVG, PNG, and PDF are each permitted only under an exact
profile with direct evidence. Typst and TikZ reject required icon uses. The implementation
does not claim generic image, raw SVG, package acquisition, renderer-local lookup, or
icon-only required semantics.

## I350-1 — Typed catalog, secure asset closure, and materialization

**Files:** add `schemas/icon-catalog-v0.1.schema.yaml`; successor
`schemas/render-context-v0.10.schema.yaml`; update schema inventory/package resources;
`presentation/contracts/resources.py`, `presentation/model/closure.py`,
`usecases/materialize.py`, Draft/CLI ingress where applicable; focused schema/closure/
materializer tests.

1. Add `IconCatalogContract`, immutable entry/source records, and optional typed Context
   `inputs.iconCatalog` edge. Preserve v0.9 parsing for existing closure evidence; v0.10
   is required for a catalog-bearing Context.
2. Validate a closed lexical `body.icons` map of namespaced IDs. Require class, safe
   Store-relative address, SHA-256, positive viewport, and alternative. Reject unknown
   keys, bad namespace, duplicate semantic binding, unsafe/escaping address, identity
   mismatch, absent asset, and non-catalog reference kind with named diagnostics.
3. Generalize the closure's packaged-font-only asset handoff into an ordered verified icon
   asset map rooted in the immutable snapshot. Copy only catalog-declared verified bytes
   in `copy_context_closure`; do not scan directories or follow symlinks. Extend the
   normalized closure/manifest evidence with catalog and asset identities.
4. Add tests for both asset kinds, tampering after pin, missing bytes, parent traversal,
   source/catalog revision mismatch, materializer copying, and no extra asset copied.

**Acceptance:** both source classes have a typed, immutable closure; no renderer can
receive an authoring path; public materialization reproduces or rejects byte-for-byte.

## I350-2 — Bounded normalization, Icon primitive, and exact target profiles

**Files:** add `presentation/icons/*` parser/normalizer contracts;
`presentation/scene/model.py`, `presentation/scene/v05_builder.py`,
`presentation/scene/visual_capabilities.py`, `presentation/renderers/v05_svg.py`,
render registry/PDF route and tests.

1. Implement a no-network standard-library SVG parser that accepts only the specified
   root/group/path subset, normalizes finite M/L/H/V/Q/C/Z commands to absolute vector
   commands, and enforces limits. Implement PNG signature/IHDR validation and limits
   without treating metadata as policy. Unit-test all forbidden syntax/classes and command
   edge cases.
2. Add a closed `Icon` Scene payload separate from layout `PathCommand`: icon vector
   commands include cubic and close without widening routing/path semantics. Scene carries
   asset identity, payload, transformed bounds, resolved paint, decorative state, and
   alternative; it has no catalog/path lookup. Add structural tests that Scene does not
   import normalizer, font metrics, or placement computation.
3. Replace the separate-profile idea with coherent `visual/v0.7-{svg,png,pdf}` negotiation.
   SVG/PNG v0.7 extend the matching v0.6 profile with `icon.vector` and `icon.raster`.
   Characterize the real PDF serialization of one vector and one PNG icon. Add v0.7-pdf
   only if it preserves both; otherwise retain explicit PDF rejection. Ensure v0.6
   gradient/shadow evidence remains unchanged and no profile silently upgrades.
4. Serialize normalized vectors as completed SVG paths and raster payload as identity-closed
   embedded data; serialize accessibility metadata from Scene only. Characterize SVG,
   resvg-derived PNG, and—if admitted—PDF output. Reject baseline/Typst/TikZ and all
   unsupported required icon capability before adapter invocation.

**Acceptance:** a target adapter can serialize Icon only from complete Scene data; SVG and
PNG evidence passes for vector and raster; PDF claim is either direct evidence-backed or
explicitly rejected; hostile source reaches no adapter.

## I350-3 — View selection and Layout composition

**Files:** successor `view-v0.11` schema/contract; existing Theme v0.5 `metrics` bindings; normalized content,
surface composer/placements, scene projection, and focused architecture tests.

1. Add closed `View.iconBindings` entries keyed by source, placement, catalog ID, and
   decorative state. Validate source existence/placement eligibility after Projection;
   View chooses icon identity, Theme only binds `icon.size`, `icon.gap`, and paint/finish
   tokens. No direct coordinate, text, target, or raw asset field is admitted.
2. Add typed Layout icon placement results for an existing label family and an existing
   semantic mark. Leading label layout reserves size/gap before measure/wrap/ellipsize and
   yields icon bounds plus existing text layout; mark layout yields completed bounds/ports.
3. Reduce Scene to projection of those completed placements. Add tests rejecting Scene
   text measurement, available-width decisions, icon binding lookup, or icon coordinate
   selection. Test baseline/wrap/overflow and source/alternative semantics.

**Acceptance:** a View-bound object has a leading label icon and a mark in the same closed
render; changing available width changes Layout output only; Scene does not reflow or
select icons.

**Correction:** Theme v0.5 already owns an open, namespaced `metrics` map whose values
are validated named number tokens. `icon.size` and `icon.gap` therefore require no Theme
v0.6 syntax or compatibility layer. View v0.11 is still necessary because icon identity
and occurrence are semantic/View authority; the implementation uses current Theme metrics
for concrete treatment and records no new Theme authority.

## I350-4 — Reusable public evidence and release gate

**Files:** a Controller Z (or new purpose-specific) catalog, SVG/PNG assets, v0.10/v0.11/
v0.6 resources, exact contexts, generated evidence, gallery text, and acceptance tests.

1. Add a public fixture with distinct normalized vector and PNG icons, one decorative
   leading label and one meaningful mark with textual equivalent/alternative. Pin every
   asset identity and demonstrate materializer closure copying.
2. Regenerate only intentional SVG evidence and inspect the diff. Add byte checks, SVG
   accessibility checks, raster/image checks, malformed asset and target-profile rejects,
   and PDF checks conditioned on the I350-2 admission decision.
3. Run focused icon/schema/closure/Layout/Scene/renderer/materializer tests as one batch,
   then the full pytest suite, conformance, public materializer checks, isolated wheel
   smoke, and the Ubuntu/macOS CI workflow. Review the complete change for ownership,
   profile truthfulness, no generic-image leak, and no unclosed asset read.

**Acceptance:** UC-33 evidence names both classes, both placements, all supported targets,
and every rejected target. #350 closes only after the published release review confirms
all gates and the GitHub CI result.

## Publication units

Publish each completed slice serially after inspecting remote `main`, diff, commit, and
fast-forward status: I350-1 closure; I350-2 primitive/profile; I350-3 Layout/View;
I350-4 evidence/release review. Any design deviation returns to the design plan,
Specification 64, and architecture review before code resumes.

## Completion evidence (2026-09-23)

- I350-1: `0137780` — catalog/context schemas, typed closure asset normalization,
  identity/path checks, and materializer copying.
- I350-2: `7a8eebf` — bounded SVG/PNG normalizer, `Icon` primitive, SVG serialization,
  and exact v0.7 SVG/PNG profile admission.
- I350-3: `5879d41` — View v0.11 semantic icon bindings and Layout-owned completed
  leading-label/mark placements.
- I350-4: this release-evidence commit — public Controller Z vector/raster fixture,
  generated SVG, vocabulary/accessibility/profile gates, and release review.

Focused icon/release tests: `49 passed`.
Full suite: `505 passed, 11 skipped`.
Wheel build and isolated resource smoke: passed. PDF has no v0.7 profile because it was
not independently admitted; baseline/PDF/Typst/TikZ reject required icons before adapter
output. This is an explicit fidelity boundary, not a degraded fallback.
