# Implementation Plan — Orientation Ingress and Completed Geometry (#412)

**Status:** approved for implementation by the 2026-09-25 correction design
and architecture review.

## Scope and release rule

This plan replaces the earlier broad I412-1 outline.  It implements only the
versioned contracts and finite 90-degree rotated horizontal text defined by
`issue-412-orientation-ingress-correction-2026-09-25.md`.  Each slice is a
reviewable fast-forward publication.  Later slices must start only from the
merged preceding slice.  No compatibility reader for View v0.17, Layout
Profile v0.7, or Scene v0.4 is added.

## I412-1 — Contract migration and typed ingress

**Files/areas**

* add `schemas/view-v0.18.schema.yaml`, `schemas/layout-profile-v0.8.schema.yaml`,
  and `schemas/scene-v0.5.schema.yaml`;
* update schema/resource inventories, packaging manifests, contract resource
  maps, closure validation, parsers, and typed resource records;
* migrate all public Views to v0.18 with explicit axis-label orientation and
  table-header orientation; migrate all public Layout Profiles to v0.8 with
  both explicit flow declarations;
* replace typed `writing_mode` data with review-surface and dependency-network
  direction fields; add typed orientation to `AxisLabelIntent` and
  `TableColumnContent`.

**Acceptance**

* old version declarations reject at the resource boundary and no live map or
  public resource refers to them;
* parser/normalization tests prove typed finite values, including invalid
  orientation/direction rejection;
* dependency-network snapshots preserve horizontal behavior and retain a
  dedicated test for each permitted network direction;
* all unrelated public contexts remain materializable before regeneration.

## I412-2 — Layout-owned completed geometry

**Files/areas**

* centralize `TextOrientation -> rotationDegrees` and four-corner bounds in
  the text-placement module;
* require/validate the orientation/angle pair in `TextPlacement` and Scene
  `TextLayout`; update Scene construction and schema serialization to v0.5;
* make `axis_label_fits` and auto-form/thinning selection consume completed
  occupied measurements; allocate axis lanes before baseline selection;
* make table allocation measure headers with orientation, reserve completed
  header block extent before rows, and preserve cell-horizontal behavior.

**Acceptance**

* focused unit tests cover horizontal, clockwise, counter-clockwise, and
  multiline bounds/pivots, with invalid pairs rejected;
* rotated axis and table-header tests prove fit/collision/overflow against the
  completed rectangle, including no header/data-row overlap;
* unchanged horizontal requests retain their previous layout measurements and
  diagnostics except for the versioned Scene representation;
* Scene projection has no font-metric, orientation-angle mapping, or layout
  fitting import.

## I412-3 — Materializers, corpus, and evidence

**Files/areas**

* add target projection support for SVG, Typst, and TikZ; verify SVG-derived
  PNG/PDF use the source transform;
* add one deliberate public rotated axis/header corpus fixture and update its
  View/Profile resource declarations;
* regenerate affected Scene/SVG/public materializer evidence, inventories, and
  generated-artifact checks; publish an English #412 acceptance review.

**Acceptance**

* adapter tests assert the exact supplied degree and baseline pivot per target
  and fail for adapter-side inference or text measurement;
* the designated public artifact contains deliberate rotation and its
  Scene bounds agree with Layout; unrelated artifact differences are reviewed;
* focused suites, full pytest, conformance, structural tests, public
  materializer checks, generated SVG diff review, built-wheel smoke, and the
  applicable three-platform CI all pass;
* acceptance review maps every Issue #412 criterion to authoritative evidence
  before the issue is closed.

## Execution order and stop conditions

1. Implement, test, review, and publish I412-1.
2. Re-read the live contract migration and implement I412-2.  If table header
   reservation reveals an incompatible slot model, stop implementation and
   return to correction design rather than adding an adapter or surface-local
   workaround.
3. Implement I412-3, regenerate once as a batch, then run release gates.
4. Fetch `origin/main`, check exact ahead/behind and diff before every push.
   Stop on remote movement, non-fast-forward, unrelated generated changes, or
   any design drift.
