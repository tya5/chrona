# Design — Semantic-to-Visual Realization (#414, #402, #413)

**Status:** Design complete; pending cross-architecture review and an
implementation plan.

## Decision

A visual distinction is selected as a finite semantic identity before Scene,
travels on the existing completed placement, and is resolved by the semantic
registry only during Scene projection.  Theme supplies paint for that resolved
role; it never receives an arbitrary fact object or evaluates a predicate.

`TextPlacement.semantic_id`, `ShapePlacement.semantic_id`, and
`RelationPlacement.semantic_id` are the required projection boundary.  Empty
or inferred semantic identities are invalid for a placement that reaches Scene.
Scene must look up the supplied identity and must not infer a semantic from a
placement ID, source text, annotation purpose, row, column, or a projection
role tuple.

## Finite realization registry (#414)

Add a source-owned finite `RealizationFamily` registry alongside the semantic
registry.  One entry declares:

| Field | Meaning |
| --- | --- |
| `family_id` | stable, reviewable semantic family name |
| `admitted_states` | finite state identities that can be selected before Scene |
| `placement_kinds` | text, shape, and/or relation consumers |
| `intentional_equivalences` | explicit state-to-semantic sharing with a reason |
| `corpus_requirement` | states that require a public realization |

The coverage generator reads this registry, normalized corpus resources, and
committed Scene primitives.  Its report is a measurement and triage artifact,
not a renderer oracle: it reports admitted state cardinality, selected state
cardinality, realized Scene-role cardinality, slide evidence, and documented
equivalences.  A state can be `not-applicable` only when the View does not
admit that family; a selected state with no primitive is a `gap`.  It does not
claim that two states need distinct roles unless the registry marks their
equivalence as non-intentional.

This replaces #414's historical aggregate ratio with an auditable table.  It
does not inspect SVG, pixels, host fonts, or adapter behavior.  Existing
presentation coverage remains responsible for schema vocabulary and slot
evidence; the realization report is a separate generated, checked document.

## Table-cell fact realization (#402)

### Typed input

Replace the bare `(object_id, column_id, content)` table-cell content tuple
with a typed cell record containing `object_id`, `column_id`, rendered content,
and `semantic_id`.  The review-content normalizer owns selection because it is
where a View column source meets the projected item fact.  Layout copies that
identity to its measured `TextPlacement`; it does not choose paint or inspect a
Theme.  Scene maps it through `semantic_binding`.

The allowed mapping is intentionally narrow:

| View column source | projected fact state | selected semantic identity |
| --- | --- | --- |
| `{comparisonFacet: finishDelta}` or `{facet: finishDelta}` | ahead / on-plan / behind / unavailable | `varianceAhead` / `finishDelta` / `varianceBehind` / `tableCell` |
| `{comparisonFacet: missingActual}` | observed / missing | `tableCell` / `missingActualCell` |
| all other built-in, custom, scenario, path, and title sources | any | `tableCell` |

`variance-on-plan` remains a projection state; its output identity is the
already declared `finishDelta` semantic, whose Scene role is
`variance-on-track`.  This gives state and visual vocabulary distinct names
without duplicating an on-plan role.  A missing/unknown finish value is not
on-plan and remains neutral.  `missingActualCell` is a new table-text semantic,
not the mark semantic `missingActual`, so its theme treatment can be legible in
a table without changing missing-observation marks.

No compatibility reader is retained for the old tuple form.  All content
constructors and tests migrate atomically.

### Invariants

1. A completed table text placement has a nonempty semantic identity.
2. A semantic identity selected for a cell is legal for its declared source;
   custom data cannot acquire variance paint through an incidental item role.
3. Rendering and ellipsizing preserve the selected identity; text content is
   never used as an input to role selection.
4. Scene emits the role specified by the supplied semantic binding, not a
   generic `tableCell` fallback.

## Annotation realization (#413)

### Typed annotation presentation

Normalize each annotation to an `AnnotationIntent` with a finite `purpose`.
Layout derives an `AnnotationPresentation` before it emits geometry:

| Purpose | box semantic | text semantic | leader semantic | terminal |
| --- | --- | --- | --- | --- |
| `callout` | `annotationCalloutBox` | `annotationCalloutText` | `annotationCalloutLeader` | none |
| `highlight` | `annotationHighlightBox` | `annotationHighlightText` | none | none |
| `note` | `annotationNoteBox` | `annotationNoteText` | `annotationNoteLeader` | none |
| `explanatory-arrow` | `annotationArrowBox` | `annotationArrowText` | `annotationArrowLeader` | target arrow marker |

Each identity has its own finite semantic-registry binding.  Box, text, and
leader therefore remain independently themeable.  The purpose may intentionally
share paint values in a shipped Theme, but the registry and Scene retain the
distinction; a shared result is a documented Theme choice, not lost meaning.

`AnnotationPresentation` is retained in completed placement provenance so
Scene does not derive any role from `annotation-*` IDs.  The existing generic
`annotation`, `annotationBox`, `annotationText`, and `annotationLeader`
semantics are removed from this review-surface path rather than kept as a
parallel fallback.

### Route ownership and terminal geometry

Add a finite annotation-specific route policy to the Layout Profile, for
example `annotationRouting.maxBends` and `annotationRouting.maxDetourRatio`.
It is measured against only annotation-box obstacles and has no effect on a
dependency path.  Layout runs the existing completed orthogonal route and the
existing route-quality predicate with this policy.

For `explanatory-arrow`, Layout obtains the target marker geometry from the
purpose's Theme terminal role and writes it to
`RelationPlacement.marker_end`.  The relation path is otherwise an ordinary
completed path.  Scene and SVG receive a marker value; neither spells an arrow
marker name.  Targets without marker capability follow the current completed
Scene capability guard, not a silent plain-line fallback.

## Corpus and migration

One Controller Z annotation slide will exercise all four purposes, including an
arrow terminal, independent box/leader treatment, and divergent callout/note
paint.  One HALCYON table slide will contain ahead, on-plan, behind,
unavailable, observed, and missing column facts for the allowed sources.
Themes declare every newly introduced semantic role.  Regenerated Scene/SVG
bytes and the realization report are committed atomically.

## Boundaries deliberately not expanded

* no Theme `when` clauses, expressions, arbitrary selector language, or access
  to raw Project facts;
* no paint selection in Scene, SVG, PNG, or other adapters;
* no generic mapping from every `ReviewItem.roles` value to every table column;
* no new primitive kind, SVG-specific arrowhead, or renderer-owned routing;
* no claim that arbitrary annotation shapes, rich text, or automatic semantic
  differentiation are part of this change.

## Acceptance criteria

1. The generated realization report is deterministic and records each
   many-to-one treatment with a reason.
2. Variance and missing-observation table cells realize their finite selected
   semantics, while neutral sources remain `tableCell`.
3. Each annotation purpose reaches distinct completed box/text/leader
   semantics; `explanatory-arrow` has a completed marker end.
4. Scene structurally rejects semantic reconstruction from placement identity
   and projects only Layout-completed semantics.
5. Corpus, public materializers, full test suite, conformance, installed wheel,
   generated-SVG review, and three-platform CI demonstrate the contract.
