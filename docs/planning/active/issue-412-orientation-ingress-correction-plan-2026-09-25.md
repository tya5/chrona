# Design Correction Plan — Orientation Ingress and Completed Geometry (#412)

**Status:** active correction plan; implementation remains unauthorized.
**Supersedes:** the under-specified #412 ingress in the 2026-09-25 typography
design and implementation plan.

## Trigger

The accepted cross-issue design says that a View declares finite label/header
orientation, that Layout supplies completed occupied bounds and a rotation
angle, and that adapters merely serialize the supplied transform.  The live
View v0.17 contract, however, has neither an axis-label orientation member nor
a table-header orientation member.  The existing plan also names Layout
Profile v0.8 without specifying the exact replacement for the misleading
`writingMode` field or the Scene-version boundary for a required angle.

Adding any of those fields while implementing would make syntax, migration,
and geometry policy accidental.  This correction completes that missing design
before I412-1 begins.

## Evidence and non-goals

* Issue #412 requires 90-degree rotated horizontal runs, matched measured and
  painted geometry, and a truthful disposition of the present `writingMode`.
* View v0.17 axis labels contain only form, alignment, and overflow; its table
  columns contain no header orientation.  `TableColumnContent`,
  `AxisLabelIntent`, and `TextPlacement` therefore cannot transport an
  orientation decision today.
* `writingMode` currently reaches only dependency-network axis assignment.  It
  never changes text shaping or adapter output, so its two vertical values are
  not a text-writing capability.
* This work does not add CJK vertical shaping, glyph-orientation selection,
  arbitrary angles, adapter-owned transforms, or orientation for ordinary
  table cells, plot labels, annotations, relations, legends, or notes.

## Design questions to close

1. Define View v0.18's only two orientation ingress points: `axis.tiers[]`
   label declarations and `tableColumns[]` header declarations.  Both must be
   finite and explicit in every migrated public View.
2. Define Layout Profile v0.8's truthful split between the review-surface
   horizontal flow and dependency-network direction.  It must remove
   `writingMode`, must not name vertical text, and must preserve the network's
   existing finite directional capability under a network-specific member.
3. Define a single completed text transform: finite orientation, exact
   `rotationDegrees`, baseline pivot, and physical occupied bounds.  Specify
   the transform equations for both 90-degree directions and the rule for
   multiline blocks.
4. Define the required Scene v0.5 representation and adapter contract so that
   SVG, SVG-derived PNG/PDF, Typst, and TikZ receive a Layout-selected angle,
   never infer one.
5. Define table and axis fitting against occupied dimensions, including header
   block reservation and axis tier lane allocation.  A rotated run must not
   fit horizontally then collide after paint.
6. Select a public corpus fixture that demonstrates rotation intentionally,
   while all unrelated generated artifacts remain byte-stable.

## Required design outputs

The correction design must contain:

* versioned schema/data-model deltas and a no-reader migration rule for View
  v0.17, Layout Profile v0.7, and Scene v0.4;
* an ownership table from View through adapters;
* exact geometry and diagnostics, including table/axis overflow paths;
* the interaction with #404 group-column labels, which will consume the same
  completed text facility later without reopening #412;
* a test/evidence matrix covering schema rejection, normalization, occupied
  geometry, collision/overflow, Scene projection, all textual materializers,
  and a generated corpus artifact; and
* an architecture review explicitly checking presentation/layout/scene/
  materializer separation and the planned #404, #405, and #411 boundaries.

## Publication sequence

1. Publish this correction plan.
2. Publish the completed English correction design.
3. Publish its architecture review.
4. Publish a replacement I412-1 implementation plan with independently
   reviewable schema/model, Layout/Scene/adapters, and corpus/release slices.
5. Only then implement and publish those slices serially.

## Acceptance of the correction phase

The phase is complete only when a future implementer can add neither a View
orientation member nor a rendering transform without violating a published
versioned contract, and when the design states how #404 reuses the facility
without inventing a second text-orientation path.
