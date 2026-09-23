# Design Plan: Presentation Design Space and Progressive Authoring (#338)

## Verified starting point

The published progressive-authoring design defines one source-format facade
that normalizes a pinned preset and a closed binding into the ordinary typed
Project, Actual Set, View, Theme, Color Scheme, Layout Profile, Render Context,
Layout, Scene, and renderer pipeline.  `authoring-workspace/v0.1` has exactly
two mutually exclusive modes: guided binding or complete explicit resources.
The normalizer is the sole reader of guided syntax.

The current guided vocabulary is deliberately conservative:

| Binding member | Effective resource owner | Current constraint |
| --- | --- | --- |
| `view.window` | View | Replaces the effective window with an explicit range. |
| `view.grouping` | View | Selects `objectType` or `none`. |
| `view.visibility` | View | Merges only declared visibility members. |
| `view.annotations` | View | Appends logical View annotations with unique IDs. |
| `theme.colorScheme` | Color Scheme selection | Must be declared compatible by the pinned preset. |

The preset currently identifies default View, Theme, Color Scheme, and Layout
Profile resources plus compatible color schemes.  It does not own Project
content, scheduler policy, renderer configuration, geometry, a mutable package
selector, or an arbitrary override mechanism.  The normalizer validates the
result by re-entering the existing resource contracts.  Materialization writes
the complete effective explicit bundle, checks byte-equivalent rendering, and
records preset, binding, normalizer, and resource identities in a receipt.

Existing resource vocabulary is broader than guided authoring.  View owns
selection, grouping, ordering, time window, comparison facets, visibility,
axis/time presentation, annotations, table columns, and row intent.  Layout
Profile owns writing mode, region/slot composition, sizing, spacing, placement,
overflow, and routing bounds.  Theme and Color Scheme own visual role bindings,
typography, marker/pattern, stroke, opacity, metrics, and colors.  Layout
derives placement geometry; Scene derives renderer-neutral primitives.

## Design questions

1. Define a compact, stable Presentation Design Space taxonomy that assigns
   every current presentation setting to one existing architectural owner.
2. Distinguish author-selectable presentation intent from Layout-derived
   geometry and renderer realization, without creating a parallel model.
3. Decide whether the current resource schemas already express each taxonomy
   member, or whether a versioned successor is necessary; do not add syntax
   merely to mirror an internal implementation detail.
4. Define how a preset denotes a named validated point in the Design Space
   using ordinary resources and typed policies rather than renderer options.
5. Define the normative Stage-2 capability and compatibility matrix.  Preserve
   the current conservative set unless an added choice has a clear owner,
   deterministic normalization rule, and preset-declared compatibility.
6. Specify field-specific precedence, provenance, and materialization for all
   allowed choices, including the rule that an explicit bundle has no live
   preset inheritance.
7. Demonstrate that distinct presets/design combinations can reuse an identical
   Project and scheduling result, and trace the result to UC-22 through UC-28.

## Non-negotiable architectural constraints

* Project, Temporal, Scheduling, Actual, and dependency semantics remain
  independent of presentation choices.
* View remains the owner of content selection and presentation intent; Layout
  remains the owner of placement and routing; Theme/Color Scheme remain owners
  of appearance; Scene remains derived and renderer-neutral.
* A Design Space value must not express coordinates, resolved dates, font
  metrics, routes, target-local options, or a generic YAML patch.
* Guided normalization terminates in the current typed closure.  It cannot
  introduce a second scheduler, Scene model, preset resolver, or implicit
  fallback/default source.
* Identical immutable inputs, environment, and target have identical effective
  closure and output.  Preset upgrades are explicit identity changes.
* Stage 3 is complete, atomic, provenance-preserving, and one-way: an explicit
  workspace remains on the ordinary explicit route (UC-28).

## Design method and required artifacts

1. Publish a design specification defining the taxonomy, its terms, and an
   owner map for the present View, Layout Profile, Theme, and Color Scheme
   vocabulary.  Record cross-layer observations as either valid hand-offs or
   design defects; do not conceal a defect with duplicated configuration.
2. Define a preset mapping model and a capability matrix for preset, guided,
   and explicit stages.  For each guided capability, state the compatibility
   predicate, normalization target, merge law, diagnostic boundary, and
   provenance record.
3. Define materialization and traceability acceptance: multiple named preset
   points reuse one semantic Project/schedule fixture; guided changes preserve
   their identities; materialized output is complete and byte-equivalent.
4. Review the proposal against the existing #222 three-stage design, resource
   contracts, Layout/Scene boundary, materialization closure rules, and
   UC-22--UC-28.  The review must explicitly decide whether a schema successor
   is required before implementation.
5. Only after the design and review are published, publish an implementation
   plan that separates any schema/contract, normalizer, fixture, and command
   changes into independently reviewable slices.

## Acceptance for this design phase

This phase is complete only when the published design and architecture review
provide: a normative taxonomy; one owner for every dimension; a complete
guided capability matrix; precedence/provenance/materialization rules;
UC-22--UC-28 traceability; a schema-sufficiency decision; and explicit evidence
that no proposed choice crosses semantic, geometry, or renderer boundaries.
No product schema, normalizer behavior, or public example changes belong to
this plan-only phase.
