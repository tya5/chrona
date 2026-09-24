# Presentation Design Space

**Status:** Proposed
**Depends on:** [06 View Model](06-view-model.md), [07 Style/Theme](07-style-and-theme.md),
[08 Scene](08-scene-and-rendering.md), [13 Presentation Format](13-presentation-format.md),
[33 Intent-Oriented Layout](33-intent-oriented-layout.md), and
[51 Progressive Authoring](51-progressive-authoring.md).
**Owns:** the taxonomy that connects ordinary presentation resources to preset,
guided, and explicit authoring stages.  It owns neither a second presentation
resource nor any semantic, geometry, or renderer authority.

## 1. Decision

A Chrona presentation is described by a finite **Presentation Design Space**.
Each dimension is an intent-level choice owned by an existing resource boundary.
A preset is a named, validated point in that space, represented by its exact
ordinary resource references.  Guided authoring exposes only the compatible
subset declared by this specification; explicit authoring owns the complete
ordinary resource bundle.

The Design Space is a taxonomy and validation vocabulary, not a new run-time
closure layer.  The only evaluation path remains:

```text
workspace + pinned preset + binding
  -> Authoring Normalizer -> Project / Actual / View / Theme / Scheme / Layout / Context
  -> Scheduler -> View -> Layout -> Scene -> renderer
```

## 2. Taxonomy and ownership

| Dimension | Intent vocabulary and present resource fields | Authoritative owner | Explicitly not owned |
| --- | --- | --- | --- |
| Content | surface; selection; grouping; ordering; time window; comparison; table columns; logical annotations; visibility; links | View | Project facts, schedules, coordinates |
| Composition | writing mode; region/slot structure; tracks, sizes, gaps, padding, alignment, anchoring; overflow; routing bounds | Layout Profile | selected content, Theme, resolved geometry |
| Visual grammar | semantic mark, relation, comparison, table, range, and annotation forms selected by View intent and completed by the presentation semantic registry | View plus the existing semantic-presentation contract | Theme tokens, SVG/TikZ syntax, paths/routes |
| Appearance | color scheme; color bindings; typography; markers; patterns; opacity; stroke; metrics | Theme and Color Scheme | selected facts, layout coordinates, renderer fallback |
| Derived adaptation | axis fitting; row sizing; text measurement; collision handling; label placement; route calculation; primitive geometry | Layout | persistent authoring state |
| Realization | renderer target encoding and capability validation of completed Scene | renderer adapter | Theme lookup, policy selection, semantic mutation |

The first four rows are the selectable Design Space.  The last two rows are
consequences of those choices and the immutable render context; they cannot be
exposed as preset or binding fields.  `density` is therefore not an independent
geometry control: it is a named View layout intent and/or Layout Profile choice
whose effect is derived by Layout.  `orientation` is a Layout Profile writing
mode, not a View or renderer switch.  A label-side preference is View intent;
its coordinate is Layout output.

The current resource schemas cover these owners without duplication:

* View v0.10 supplies the Content vocabulary and the author-facing parts of
  Visual grammar: `surface`, selection/grouping/ordering/window/comparison,
  visibility and fallbacks, axis/time presentation, rows, columns, and annotations.
* Layout Profile v0.4 supplies Composition through named slots and containers,
  flow/grid/overlay structure, writing mode, intent tokens, overflow, and
  relation-routing bounds.
* Theme v0.4 and Color Scheme v0.2 supply Appearance through semantic role bindings,
  typed values, and color choices.  Completed paint remains Scene-derived.
* The semantic presentation contract selects the closed semantic primitive
  families; Scene completes them to renderer-neutral forms and paint.

No Design Space member may carry a Project object, Actual observation, calendar,
dependency meaning, resolved date, pixel or scene coordinate, font metric,
route, renderer option, arbitrary YAML path, host default, or mutable registry
selector.

## 3. Presets

`presentation-preset/v0.1` names one exact default View, Theme, Color Scheme,
and Layout Profile plus a finite set of compatible Color Schemes.  This is the
persisted representation of a named Design Space point.  Its `id` is a useful
human name; its authoritative meaning is the exact acquired resource identities
and package version.  A preset does not need a duplicate flat dimension map.

An implementation may expose a derived, immutable `PresentationDesignSummary`
for inspection, gallery curation, GUI, or AI proposals.  It must be calculated
only from the validated effective ordinary resources, use the taxonomy in
section 2, and retain the resource identities from which every value arose.  It
is not an authoritative closure input and cannot introduce a second resolver.

### 3.1 Inspection summary

The first bounded consumer of this taxonomy is the public design gallery.  Its
inspection result is conceptually shaped as follows; this is an output contract,
not another authored resource or schema accepted by render evaluation:

```yaml
format: chrona/presentation-design-summary/v0.1
provenance:
  origin: explicit | guided | materialized
  view: {id: ..., kind: view, contentIdentity: sha256:...}
  layout: {id: ..., kind: layout-profile, contentIdentity: sha256:...}
  theme: {id: ..., kind: theme, contentIdentity: sha256:...}
  colorScheme: {id: ..., kind: color-scheme, contentIdentity: sha256:...}
dimensions:
  content: {...}
  composition: {...}
  visualGrammar: {...}
  appearance: {...}
```

Each dimension contains only finite, authored intent that can be read directly
from one of the effective View, Layout Profile, Theme, or Color Scheme
contracts.  Content may report surface, selection/grouping/ordering/window,
comparison, visibility, table and annotation intent.  Composition may report
writing mode, declared container/slot vocabulary, overflow and routing intent.
Visual Grammar may report the selected closed semantic presentation families.
Appearance may report the Theme, Scheme, and declared role/token vocabulary.

The summary reports a value together with the identity of its owning resource;
it never flattens those values into a second editable configuration bag.  A
dimension or member that has no stable finite interpretation is omitted rather
than inferred.  In particular, it MUST NOT contain Project or Actual facts,
resolved dates, measurements, font metrics, row sizes, collision decisions,
coordinates, routes, Scene primitives, renderer capability fallback, cache
location, package selector, or arbitrary resource paths.

Summary construction accepts only a complete validated effective resource
bundle.  It is pure: it neither reads a registry/directory nor causes
normalization, materialization, scheduling, Layout, Scene construction, or
rendering.  A failed inspection returns a stable diagnostic such as
`E_DESIGN_SUMMARY_INPUT`, `E_DESIGN_SUMMARY_IDENTITY`, or
`E_DESIGN_SUMMARY_UNREPRESENTABLE`; it cannot make an otherwise valid render
fail.  The summary is recomputed from the closure supplied to the inspection
caller and is never persisted as a replacement for its provenance.

The current schemas are sufficient for this design: they can express every
effective choice through its owner and the preset already pins the complete
resource bundle.  A versioned successor is required only when a new,
independently selectable intent cannot be represented by View, Layout Profile,
Theme, or Color Scheme without cross-owner duplication.  A successor must add
the owner-field first, then an optional preset declaration; it must not add a
renderer configuration bag or generic override map.

## 4. Stage capability and compatibility matrix

| Dimension | Pinned preset | Guided binding | Explicit resources |
| --- | --- | --- | --- |
| Content window | default View value | allowed explicit range | allowed by View schema |
| Content grouping | default View value | `objectType` or `none` only | allowed by View schema |
| Visibility and logical annotations | default View value | allowed closed members / additive unique annotations | allowed by View schema |
| Color scheme | default and finite compatible set | allowed only when declared compatible | any schema-valid explicit Scheme reference |
| Selection, ordering, comparison, rows, columns, axis, time presentation | default View value | not exposed | allowed by View schema |
| Composition / layout profile / writing mode / routing | default Layout Profile | not exposed | allowed by Layout Profile schema |
| Visual grammar variants | effective View and semantic registry | not exposed | allowed only through their owning versioned contract |
| Typography, marker, pattern, shape, surface, stroke, opacity, spacing metrics | effective Theme/Scheme/Layout values | not exposed | allowed by owning Theme/Scheme/Layout schema |
| Render target/environment | preset closure context | not exposed | allowed only through the ordinary explicit Render Context policy |
| Geometry, measurements, routes, Scene/renderer form | derived | never exposed | never authored |

Guided compatibility is field-specific and closed.  A preset supports all and
only the matrix's allowed binding members.  Color Scheme compatibility is the
preset's explicit finite list.  Other permitted members need no per-preset
fallback because their normalizer operation is total only when the resulting
View validates; an invalid normalized View rejects rather than degrading the
preset.  Broadening guided mode requires a new matrix row with: an existing
owner, a finite typed vocabulary, a structural normalizer operation, a
deterministic compatibility predicate, and evidence that Project/Scheduling
identity remains unchanged.

## 5. Precedence, provenance, and materialization

The merge law remains field-specific rather than generic:

```text
preset default resources < validated guided binding operation < one materialized explicit bundle
```

Window replaces the View window; grouping replaces the grouping choice;
visibility shallowly replaces only declared visibility members; annotations
append after unique-ID validation; and a compatible scheme substitutes the
scheme resource.  No live guided document may mix inherited resources with
partial arbitrary explicit resources.

The guided closure records workspace identity, preset package identity, binding
identity, normalizer version, effective ordinary resource identities, target,
environment, and origin (`draft` or immutable).  A Design Summary, if emitted,
records the same source identities.  It does not replace closure provenance.

Materialization resolves those operations once, writes the complete effective
Project/Actual/View/Theme/Scheme/Layout/Context bundle and receipt atomically,
then proves rendering byte equivalence in the same target/environment.  The
receipt records the preset, binding, normalizer, and generated resource
identities.  Afterwards the workspace is explicit and has no preset edge;
subsequent changes use ordinary resource contracts.

## 6. Use-case traceability and required evidence

| Use case | Design Space evidence |
| --- | --- |
| UC-22 | A pinned named point normalizes into ordinary resources with no author knowledge of internal dimensions. |
| UC-23 | Compact semantic mutation changes only Project/Actual; the Design Space closure is preserved unless an explicit presentation command changes it. |
| UC-24 | Every guided choice is a matrix row and normalizes to View or Scheme without Project/Scheduling identity change. |
| UC-25 | An annotation is logical View content, never a Scene coordinate or route. |
| UC-26 | Effective resource and Design Summary provenance identify each selected point. |
| UC-27 | One complete explicit bundle and receipt preserve effective choices and byte-equivalent rendering. |
| UC-28 | An explicit project bypasses presets and guided normalization entirely. |

Implementation acceptance must include at least two named presets that reuse
the same Project and scheduling fixture while producing distinct validated
effective presentation closures.  It must also prove: the guided capability
matrix accepts its allowed rows and rejects every adjacent cross-boundary
choice; equal immutable inputs are deterministic; Stage-2-to-3 output is byte
equivalent; and an explicit fixture has no preset provenance edge.
