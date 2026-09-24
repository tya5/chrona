# Implementation Plan: Endpoint Annotation Evidence (#386)

**Status:** Proposed

**Implements:** [Endpoint Annotation Evidence design](../../design/issue-386-endpoint-annotation-evidence-design-2026-09-25.md)

## I386-1 — Annotation contract characterization

Add focused Layout and Scene-projection tests for two View v0.13 object
endpoint annotations.  Assert actual/planned finish endpoint selection,
deterministic orthogonal leader geometry, obstacle avoidance, source identity,
and annotation-specific Scene purpose/role.  Add a structural regression that
Scene/adapter modules do not import the Layout router.

**Files:** focused Layout/Scene tests and only production changes required to
express an observed missing invariant.

**Acceptance:** the test fails if a leader is routed after Layout, a finish
endpoint becomes an arbitrary bar coordinate, or a second annotation box is
ignored as an obstacle.

## I386-2 — Declared Controller Z evidence slide

Add the View, dedicated annotation-rail Layout, Context, manifest entry, and
generated SVG for the two-arrow Controller Z slide.  The new Context preserves
the executive Project, Actual, Theme, Scheme, and target closure while
selecting the annotation Layout and View.
Generate the SVG exclusively through the public materializer and inspect the
diff.

**Files:** `examples/controller-z/views/annotations.yaml`,
`layouts/annotations-review.yaml`, a matching Context, `manifest.yaml`,
generated SVG, and any identity/closure evidence required by the materializer.

**Acceptance:** both annotation purposes, box/text/leader primitives, and
object/facet/endpoint provenance occur in the output; the second route avoids
the first box; materialization is byte-identical.

## I386-3 — Release and coverage handoff

Run focused tests, all public materializers, full pytest, conformance,
generated-SVG review, and repository quality gates.  Publish an acceptance
review that records the Project-note/View-callout boundary and makes #375 the
owner of subsequent presentation-vocabulary counting.

**Acceptance:** no Project schema/scheduler change, all current corpus slides
remain reproducible, and Ubuntu/macOS/Windows CI succeeds before closing #386.
