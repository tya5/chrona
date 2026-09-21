# M28 Review Row Composition Design Plan — 2026-09-21

**Status:** Design in progress. Implementation is not authorized.

## Goal

Replace the accidental one-Project-object/one-review-row restriction with a View-owned
review-row composition model. One visible row may contain several selected Project
objects and their comparison facets, including span tasks and point milestones.

## Design sequence

1. Inventory the current Project → schedule placement → `ReviewItem` → `SceneRow`
   mapping and identify the ownership boundary.
2. Specify a versioned View row-composition contract, projection values, table-subject
   rule, deterministic member order, diagnostics, and automatic-row migration mode.
3. Reconcile the contract with Snapshot/Actual alignment, View grouping/ordering,
   Layout Manifest row geometry, Scene provenance, relations, annotations, and SVG
   serialization; record the result in the cross-boundary review.
4. Publish the completed design, then publish an implementation plan with executable
   acceptance evidence before changing runtime code.

## Non-goals

M28 does not add renderer coordinates, semantic containment, rescheduling, or an
Actual-driven forecast. It also does not choose a special case for a named example,
task type, or milestone type. Actual overlay/progress-indicator geometry is a later
presentation policy that consumes the M28 row membership model.
