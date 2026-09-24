# Issue #354 — Gallery Collection Implementation Plan

**Implements:** `issue-354-gallery-collection-design-2026-09-24.md`

**Correction:** `issues-354-355-posthoc-correction-design-2026-09-24.md`

## G354-C1 — One-axis closure correction

Extend the inventory validator with the closed dimension-to-reference map,
owner-change requirement, permitted typed supports, and stable axis-leak
diagnostic.  Re-pin the network peer with fixed Appearance, or defer it if its
public materialization fails.  Make deferred dimensions optional and generate
single-resource YAML exhibits plus generator provenance.

**Acceptance:** focused fixtures reject an owner-less comparison, an
undisclosed reference leak, invalid support, and invalid deferred metadata;
every published set passes the strict contract and materializes.

## G354-1 — Catalogue v0.2 and evidence validator

Replace v0.1 parsing in `tools/example_inventory.py` with the closed v0.2
dimension/axis contract. Validate set consistency, existing provenance, and
declared SVG evidence. Migrate all catalogue test fixtures atomically.

**Acceptance:** independent tests reject unknown/missing/mixed dimension and
axis, unpaired sets, semantic mismatch, and missing evidence.

## G354-2 — Read-only gallery generator

Add `tools/render_design_gallery.py`, deterministic index/set Markdown output,
and tests for stable peer/reference-diff rendering. Generate only from
validated catalogue and committed corpus evidence; add no runtime imports.

**Acceptance:** generator output is deterministic, shows coverage backlog and
relative evidence/provenance links, and cannot write corpus resources.

## G354-3 — Existing-evidence collection migration

Split the legacy Controller Z mixed set, add the existing Halcyon surface pair,
and materialize/pages for every immediately feasible Context pair. Review SVG
and documentation diffs together.

**Acceptance:** every set has one dimension and one axis; each pair proves
identical semantic provenance and distinct presentation provenance.

## G354-4 — New-context sets

Add only context/resources required for Four appearances, Programme at scale,
and Investigating a slip, each as an independent materializer/evidence slice.
Stop and return to design if a required View/Layout capability is absent.

**Acceptance:** public materializer reproduction, generated pages, focused
tests for each pair, then batched full suite/release gate.

## G354-5 — Deferred backlog and release

Represent sets 7–10 accurately as deferred/blocked backlog without fabricated
evidence. Run full pytest, conformance/structural gates, all declared
materializers, SVG diff audit, wheel smoke, and GitHub CI. Close #354 only when
all non-blocked sets are published and blockers are visible in the index.
