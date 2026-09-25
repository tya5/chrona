# Design Plan — Typography, Orientation, and Draft System Fonts (#410, #412, #411)

**Status:** active design plan; implementation is not authorized.

## Problem boundary

Typography values that alter glyph occupancy cannot be adapter decoration.
They must travel from a finite Theme declaration through normalization and
Layout measurement into completed `TextLayout` and every target adapter.
Likewise, a rotated horizontal run must occupy the axes on which it is
measured.  System fonts are a separate draft-only runtime concern and must not
weaken immutable Context closure or materializer reproducibility.

## Evidence from the current implementation

* `FontMetrics.width()` already accepts `letter_spacing`, but
  `ThemeTokenView.typography()`, `place_text()`, `TextPlacement`, and
  `TextLayout` carry only family, weight, size, and line height.
* `writingMode` admits two vertical values while no completed text placement,
  Scene primitive, or adapter carries an orientation.
* font locators admit only `context` and registered `package` providers, and
  the raster adapter explicitly disables host-font discovery.

## Design work packages

### D4-1 — One typed text-treatment contract (#410)

Define an immutable `TextTreatment` returned by Theme token resolution instead
of extending positional typography tuples.  It must contain family, weight,
size, line height, finite transform, em-based letter spacing, and finite
numeric spacing.  Define the canonical transformed string and feature-aware
measurement input; Layout stores both source and painted content when they
differ.  Determine the exact finite transform and numeric-spacing vocabulary,
their schema representation, diagnostic paths, and the font-metric asset data
needed to measure selected number forms without host inference.

### D4-2 — Orientation and writing-mode truthfulness (#412)

Separate surface flow/axis assignment from a `TextOrientation` carried on a
completed text placement.  Compare a clean contract that narrows unsupported
vertical writing modes with one that adds only 90-degree horizontal-run
rotation; neither may imply CJK vertical composition.  The selected design
must state occupied bounds, baseline/anchor semantics, multiline behavior,
collision/overflow consequences, and SVG/PNG/PDF/typeset projection.  It must
also choose whether the existing network-axis behavior is renamed or migrated
to a distinct finite direction field rather than preserving misleading names.

### D4-3 — Draft-only system-font resolution (#411)

Design a runtime `DraftFontResolution` boundary outside Context locator
schemas.  It resolves one requested family/weight to one actual host file,
derives metrics from that file, records nonportable provenance on the draft
render result, and supplies that exact file to raster output.  Missing or
ambiguous resolution is diagnostic; substitution is forbidden.  Immutable
Context construction, `render-review`, and `materialize` must reject the
nonportable result before evidence emission.  Specify platform-provider
abstraction, licensing-safe diagnostics, and the test seam without committing
machine paths or font bytes.

### D4-4 — Architecture and migration review

Review D4-1 through D4-3 against the authority chain and existing font closure
rules.  Document schema/version migration for every public Theme/Layout/Context
resource, required corpus evidence, package/wheel impact, and explicitly
removed superseded forms.  Publish the design and review before implementation
planning.

## Required design decisions

1. Whether `numericSpacing` is a finite OpenType-feature request, a selected
   bundled-face variant, or an explicitly deferred capability; a role may not
   request a feature that the measured asset cannot prove.
2. Whether horizontal-run rotation is delivered now.  If not, all unsupported
   `writingMode` values must be removed rather than silently accepted.
3. The draft input that names a system family without placing a host locator in
   a Context, Store snapshot, materializer closure, or generated Scene.
4. The common completed geometry that keeps SVG, PNG, PDF, Typst, and TikZ
   painting the same measured text and orientation.

## Design acceptance

The resulting English design must give a finite data model, ownership table,
cross-adapter geometry contract, immutable/draft provenance boundary, migration
impact, and corpus/test plan.  An independent architecture review must confirm
that no value is inferred in Scene or an adapter and that no system-font path
can reach reproducible evidence.

## Publication protocol

Publish this plan, the completed design, and the architecture review as
separate fast-forward commits.  Only then publish an implementation plan whose
slices each have focused tests, public evidence, and a final shared release
gate for #410/#412/#411.
