# Design Plan — Semantic-to-Visual Realization (#414, #402, #413)

**Status:** Design planning complete; implementation is not authorized.
**Programme:** P3 of `integrated-quality-programme-plan-2026-09-25.md`.

## Problem boundary

The current public corpus proves that the semantic registry and completed Scene
roles exist, but it does not prove that every meaningful distinction reaches a
paintable role.  #402 is a concrete lost distinction (the already projected
variance state is discarded for a table cell).  #413 is another (annotation
purpose is used for geometry preference but not for its box, leader, or text
treatment).  #414 must turn those observations into current, reproducible
evidence without declaring that every model field requires unique paint.

This programme consumes the established Project -> View -> Layout -> Scene ->
adapter chain.  It does not add Theme predicates, renderer inference, generic
CSS-like selectors, arbitrary presentation roles, or a second marker/routing
path.

## P3-D1 — Establish a semantic realization evidence contract

Define a finite, source-derived record for each realizable semantic family:

* semantic family and the declared states it admits;
* source boundary at which its state is selected;
* completed Scene purpose and role(s) actually emitted by each corpus slide;
* an explicit disposition for a many-to-one realization (`intentional`,
  `not-applicable`, or `gap`) with a cited reason.

The report must be deterministic, generated from normalized contracts and
committed Scenes, and remain separate from render validation.  It must not
infer facts by pixel comparison or SVG/CSS parsing.  Its registry is finite:
adding a semantic family requires declaring its admissible states and
disposition rather than silently expanding a heuristic count.

**Exit criteria:** a generated report distinguishes model-state cardinality,
realized-role cardinality, and intentional equivalence; tests prove stable
ordering, invalid registry entries, and that the report reads completed Scenes
rather than an adapter.

## P3-D2 — Carry table fact state to a completed text role

Define a typed cell-semantic selection owned before Scene:

* a column source declares whether it consumes a finite fact-state family;
* normalized Projection supplies the item state already computed for that
  family (initially finish variance and missing observation only where a
  column source admits it);
* Layout attaches the selected semantic identity to the completed text
  placement; Scene performs only registry projection;
* a source with no admitted state retains `tableCell`, so title/path/custom
  fields cannot acquire paint based on accidental item roles.

The design must resolve the naming mismatch between existing `variance-on-plan`
projection values and the declared semantic registry, and make absent versus
on-plan explicit.  It must not use the order of an item's role tuple or a
Scene-side lookup from cell text to choose treatment.

**Exit criteria:** every table placement has one finite semantic identity;
the known variance states and explicitly admitted missing state can reach
different theme roles; neutral columns retain their existing role; corpus
evidence includes all admitted distinctions.

## P3-D3 — Carry annotation purpose to independent completed treatments

Define a finite annotation presentation record in Layout with separate:

* purpose-derived box semantic;
* purpose-derived text semantic;
* purpose-derived leader semantic and terminal intent;
* annotation-specific routing policy, distinct from dependency routing.

`explanatory-arrow` consumes the completed marker/terminal representation
already established for relations.  It must not name an SVG arrowhead or infer
one in Scene.  The design must decide which purposes intentionally share a
treatment, while preserving independently stylable box and leader roles.

**Exit criteria:** each admitted purpose resolves to typed completed identities;
the arrow purpose has a completed terminal; a box and its leader can differ;
all four purposes have public corpus evidence; route constraints are owned by
the annotation Layout policy.

## P3-D4 — Atomic integration and acceptance

Implement D1--D3 as one compatibility-free presentation-contract migration.
Regenerate the coverage report and all affected public Scenes/SVGs in the same
release.  Do not ship the report with known `gap` rows for #402 or #413, or
ship new registry roles without theme/corpus materialization evidence.

Acceptance requires focused contract/Layout/Scene/report tests, full pytest,
conformance, checked generated coverage, affected materializer output checks,
one generated-SVG diff review, installed-wheel smoke, and three-platform CI.
Publish an English architecture review before the implementation plan, then an
English acceptance review before closing the three issues.

## Cross-architecture review questions

1. Can a completed placement carry semantic identity without making Layout
   choose Theme paint, and without making Scene reconstruct semantics from an
   identifier?
2. Which finite column sources legitimately consume variance or observation
   state, and how are custom fields kept neutral?
3. Is purpose-specific annotation treatment entirely representable by the
   existing marker and path contracts, or is a new completed primitive value
   required?
4. Does the evidence report distinguish an intentional shared treatment from a
   semantic distinction that was never connected to output?
5. Are all additions compatible with Specifications 07, 36, 50, 55, 63, and
   64 and the already closed #393--#399 contracts?
