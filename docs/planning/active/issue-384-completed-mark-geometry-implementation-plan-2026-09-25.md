# Issue 384 — Completed Mark Geometry Implementation Plan

**Status:** active  
**Design:** `docs/design/issue-384-completed-mark-geometry-design-2026-09-25.md`  
**Architecture review:** `docs/reviews/current/issue-384-completed-mark-geometry-architecture-review-2026-09-25.md`  
**Issue:** #384  
**Date:** 2026-09-25

## Scope and invariant

Implement only the accepted #384 geometry boundary.  The resulting public
materializer must receive Theme v0.7 structured treatments, emit completed
adapter-neutral mark/pattern/symbol geometry in Scene, and serialize or reject
that geometry through declared target capabilities.  No slice may retain a
current runtime reader for Theme v0.6 scalar marker/pattern values, a
`ScenePrimitive.shape` string, or renderer geometry selection.

Each implementation slice is committed, reviewed, and pushed serially.  Before
each push: fetch `origin/main`, check divergence and the exact commit; do not
force-push.  If a slice exposes a responsibility or migration gap, stop and
publish a design correction before resuming implementation.

## I384-1 — Atomic current-contract switch and completed SVG geometry

### Changes

1. Add `MarkerGeometry`, `PatternStroke`, `PatternGeometry`, and
   `SymbolGeometry` to `presentation.scene.model`; replace the scalar
   `ScenePrimitive.shape` and `ScenePrimitive.pattern` fields with their
   primitive-scoped completed payloads and invariants.
2. Add pure Scene geometry constructors for the finite marker/symbol catalog.
   They use only adapter-neutral `PathCommand` and completed Layout bounds.
3. Add Theme v0.7 schema and make it the sole current Theme resource mapping.
   Implement the structured marker/pattern/symbol `ThemeTokenView` accessors
   and update paint-family completion to consume typed treatment rather than
   renderer-shaped names.
4. Migrate every live Theme source, Context source map, schema fixture,
   resource contract test, vocabulary-policy entry, and generated vocabulary
   inventory from v0.6 to v0.7 in the same change.  Preserve current default
   geometry exactly.
5. Update Scene composition so dependency Paths carry `MarkerGeometry`, hatch
   Rects carry `PatternGeometry`, and all point marks carry `SymbolGeometry`
   resolved through `milestoneSymbol`.  No builder literal may select diamond.
6. Rewrite SVG definition and primitive serialization to use completed payloads
   only.  It may derive deterministic target-local IDs from completed geometry
   and paint, but cannot test a Theme/Scene name to choose a path, size, or
   transform.

### Focused verification

* Theme resource schemas reject malformed geometry and unsupported finite
  shapes at the authored token path.
* `ThemeTokenView` rejects malformed hand-built resolved data.
* Scene unit tests prove default triangle/hatch/diamond completion and
  non-default marker dimensions, hatch pitch/angle, and non-diamond symbol.
* SVG unit tests prove it serializes supplied completed geometry and contains
  no triangle/diamond/diagonal-hatch selection branch.
* `tools/vocabulary_inventory.py --check` passes with the v0.7 policy/report.
* All public materializers reproduce or intentionally regenerate their SVGs;
  inspect the generated diff to confirm the migrated defaults are byte-stable.

### Slice acceptance

The SVG, PNG, and PDF routes materialize every current corpus context from the
new Theme contract.  Scene source and SVG source have no legacy string geometry
field or hard-coded selected geometry.  Focused tests, conformance, full
`pytest`, public materializer checks, and generated-SVG diff review pass.

## I384-2 — Capability honesty and adapter evidence

### Changes

1. Add `mark.marker-geometry`, `paint.pattern-geometry`, and
   `mark.symbol-outline` to the visual-capability model.  Derive requirements
   from completed Scene primitive payloads before rendering.
2. Declare support in SVG/PNG/PDF visual profiles.  Do not alter their output
   protocol: PNG/PDF retain their documented SVG-backed realization.
3. Give direct Typst and TikZ adapter entry points declared support sets and
   validate required completed geometry.  Implement their supported completed
   forms or reject with `E_VISUAL_CAPABILITY_UNSUPPORTED`; delete comment-only
   Path success and Rect pattern omission.
4. Add independent Scene-to-SVG and Scene-to-typeset capability tests,
   including a fixture whose Theme selects a non-default marker, pattern and
   point symbol.  Add a structural test forbidding geometry-selection literals
   in adapters and scalar geometry fields in `ScenePrimitive`.
5. Regenerate all affected public materializer evidence and add a release
   acceptance review documenting exact commands, changed artifacts, and
   no-silent-degradation results.

### Focused verification

* `tests/unit/chrona/presentation/scene/test_visual_capabilities.py`
* `tests/unit/chrona/presentation/scene/test_v05_builder.py`
* `tests/unit/chrona/presentation/renderers/test_v05_svg.py`
* `tests/unit/chrona/presentation/renderers/test_v05_typeset.py`
* resource-contract, vocabulary-inventory, and public-materializer focused
  tests

### Slice acceptance

Every adapter either serializes the exact completed geometry it advertises or
fails before output with the named capability.  No target reports a successful
artifact after omitting a marker, hatch, or symbol treatment.  Focused tests,
conformance, full `pytest`, materializer byte checks, generated-SVG diff review,
and all supported-platform CI pass.

## Final issue gate

After I384-2, publish an acceptance review that checks every Issue 384
criterion against committed evidence.  Verify remote `main` and the three
platform CI results before closing #384.  Only then start #385 Phase 0; the
#385 plan must use the completed data model rather than invent a second mark
geometry representation.  Re-open #387's final acceptance review after #384,
because its vocabulary gate is not proof of adapter-neutral geometry.
