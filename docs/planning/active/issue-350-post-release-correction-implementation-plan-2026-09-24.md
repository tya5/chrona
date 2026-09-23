# Implementation Plan: #350 Post-release Correction

**Status:** Active.  **Prerequisite:** published C350 correction design and
architecture review.  Each slice is independently reviewable and publishable.

## I350C-1 — Restore executable public ingress and CI truth

Update Draft/guided profile choices, README, schema annotations, and View
dispatch reachability to their live successor contracts.  Add CLI success and
rejection tests.  Mark the old release review superseded.

**Acceptance:** a documented explicit v0.7 command renders a catalog icon;
non-admitting profiles reject; annotation and dispatch tools pass.

## I350C-2 — Correct importer/closure names and diagnostics

Resolve alias parent chains under selection, retain aliases of selected parents,
emit structured importer locations, and add deterministic closed-catalog nearest
names. Canonicalize every direct/encoded View reference at the closure ingress
before Layout. Add adversarial alias-chain, transform, unknown-reference, and failing
element tests.

**Acceptance:** no alias is silently lost by selection; diagnostics identify
catalog/icon/source stage; no lookup responsibility enters Layout or Scene.

## I350C-3 — Regenerate Material default and public evidence

Add an explicit bundle generation manifest with source version, canonical
selection, declared variant-alias parent closure, and collision-checked
short-name rules.  Regenerate the packaged
catalog, make source/notice relationship reproducible, add bounded loader and
Draft-render checks, and materialize real Material small-text/title/header
evidence.

Extend materialization with an explicit identity-pinned package-catalog
reference, then use it for public Material exact-13px table-text/title/header evidence.

**Acceptance:** no declared variant alias dangles; aliases and short names
resolve; source version is true; generated count/size limits are manifest-owned;
Material evidence is package-closed, committed and byte-reproducible; and performance is bounded
without machine-specific assertions.

## I350C-4 — Third-party semantic conformance

Commit a fixture generated from pinned `@iconify/utils` for Material alias and
transform resolution, with a documented generator/provenance.  Test Python
normalization against it without invoking Node in CI.

**Acceptance:** canonical and alias geometry/viewport semantics agree for the
fixture; fixture generation is reproducible and runtime stays Python-only.

## I350C-5 — Replacement release gate

Run focused tests, full parallel pytest, conformance, all public materializers,
generated SVG/PNG audit, isolated wheel smoke, and GitHub CI.  Update the
matrix and replacement release review only after all evidence is green.
