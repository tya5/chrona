# Issue 384 — Completed Mark Geometry Design Plan

**Status:** active  
**Issue:** #384  
**Date:** 2026-09-25  
**Scope:** Theme-owned dependency-marker, fill-pattern, and milestone-symbol
geometry through the completed Scene boundary.  This plan deliberately excludes
Scene serialization (#385), semantic-registry closure (#385), presentation
vocabulary measurement (#375), and new editorial policy (#383).

## 1. Problem and verified starting point

At `72e82e6` the public presentation route has a contradiction:

* `ScenePrimitive.shape` and `ScenePrimitive.pattern` carry string names;
* `scene/v05_builder.py` writes `"diamond"` for milestone marks and forwards
  a Theme marker name for dependency paths;
* `renderers/v05_svg.py` selects the triangle outline, marker dimensions and
  attachment point, the diagonal-hatch pitch and angle, and the diamond polygon;
* Theme v0.6 constrains the currently accepted scalar names, but it cannot
  express the geometry that SVG chooses.

The result contradicts the Scene model's claim that adapters serialize and do
not reinterpret primitives.  It also prevents a Theme from changing hatch
pitch/angle, marker size, or milestone shape, and makes a future published
Scene (#385) insufficient for another capable adapter to reproduce a surface.

The existing architecture supplies the intended ownership boundary:

```text
Theme + Color Scheme --resolved appearance--> Scene builder
Layout --completed bounds/routes------------> Scene builder
Scene builder --completed primitive geometry-> adapter serialization
```

Theme owns finite authored appearance intent; Layout owns bounds and routes;
Scene owns the completed, renderer-neutral result; a renderer owns target
syntax and declared capability only.  Project, View, Layout grammar, route
selection, and semantic-registry vocabulary are not Theme or adapter concerns.

## 2. Questions the design must settle before implementation

1. Define the finite, structured Theme values for markers, patterns, and
   milestone symbols.  They must be schema-validated at resource load and
   cannot be arbitrary SVG/XML, renderer snippets, or an open string namespace.
2. Define immutable completed Scene geometry for each treatment.  It must have
   all data required by an adapter: marker outline, dimensions and attachment;
   pattern tile, angle and stroke; and a final symbol outline or equivalent
   path.  No adapter may map a semantic name to geometry.
3. Decide how a marker's reusable local-coordinate outline and a symbol's
   bounds-relative outline are represented without leaking SVG syntax.  Reuse
   the existing renderer-neutral `PathCommand` vocabulary where it fits.
4. Define the Theme role by which planned/actual/snapshot point marks resolve
   their milestone symbol.  It must use the existing semantic registry rather
   than add direct purpose/role literals.  The #385 registry-hole corrections
   remain a separate slice.
5. State the exact capability contract for adapters that can or cannot render
   completed marker/pattern/symbol geometry.  A target must either implement
   the completed geometry or reject its required capability before rendering;
   it may not silently omit it.
6. Decide the contract migration.  Clean design takes precedence over readers
   for obsolete Theme scalar values: a successor Theme schema/resource version
   replaces v0.6 as the current runtime contract, all shipped resources migrate
   atomically, and historical schemas stay inventory-only.
7. Establish whether a completed Scene may preserve an `outline` treatment as
   an explicit no-pattern geometry result, rather than asking each adapter to
   interpret that name.  The answer must make both painting semantics and
   capability negotiation explicit.

## 3. Required design deliverables

The design phase shall publish all of the following in English.

1. A normative Issue 384 design document with data models, ownership table,
   finite vocabularies, rejection diagnostics, capability semantics, migration,
   and non-goals.
2. A whole-architecture review against Specifications 30, 34, 55, and 62,
   covering Project/View/Theme/Layout/Scene/renderer separation, closed
   semantic vocabulary, rich-primitive portability, materialization, and #385
   serialization readiness.
3. A decision record for the canonical geometry model, including an example of
   each supported marker, pattern, and milestone symbol from Theme source to
   Scene result to SVG serialization.
4. An explicit result for the typeset targets: support the completed geometry
   or expose a precise capability rejection.  The design may not retain their
   current silent omission.
5. A migration inventory for every current Theme, schema-resource mapping,
   fixture, context source map, vocabulary policy row, and generated evidence
   affected by the successor Theme contract.

## 4. Design constraints and acceptance criteria

The completed design is acceptable only if it demonstrates all of the
following.

* A Theme author can vary hatch pitch and angle, marker dimensions, and a
  milestone shape through typed data, without renderer-source changes.
* Theme loading rejects unsupported structured geometry at the Theme source
  path and names the supported finite alternatives where applicable.
* Scene primitives carry completed geometry, not `triangle`, `diamond`, or
  `diagonal-hatch` names whose interpretation remains in an adapter.
* The same completed Scene is sufficient for every adapter that advertises the
  relevant capability.  Unsupported adapters fail through capability
  negotiation before output, not by partial serialization.
* SVG-specific constructs (marker IDs, `viewBox`, `<pattern>`, SVG transforms,
  polygon syntax) do not enter Theme, Layout, or the Scene contract.
* The design does not pre-empt #385's serialized schema, #375's measurement
  policy, #383's editorial dot-grid decision, or arbitrary user-defined paths.
* Existing corpus appearance is preserved unless a documented, intentional
  policy change is required by the new contract.

## 5. Review procedure and publication gate

1. Inspect the current data flow, schema inventory, capability checks,
   type-set adapters, materializer, and all active planning/design documents
   that own the affected boundaries.
2. Write and self-review the design and architecture review against the
   criteria above.  Resolve design findings before implementation planning.
3. Commit and push the design plan first; then commit and push the approved
   design and its architecture review in a separate serialized publication.
4. Only then write an implementation plan with independently reviewable
   slices, exact files, focused tests, full-suite gate, materializer checks,
   generated-SVG comparison, and CI acceptance review.

## 6. Downstream dependency

#385 may begin only after this issue's design, implementation, verification,
and public merge establish completed marker/pattern/symbol geometry.  The final
#387 acceptance review must re-check this boundary after Issue 384, because its
declared-vocabulary gate cannot substitute for actual adapter-neutral geometry.
