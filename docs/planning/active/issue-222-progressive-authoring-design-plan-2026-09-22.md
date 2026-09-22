# Issue 222 Progressive Authoring Design Plan

## Purpose

Define a three-stage authoring facade that lets an author start with a compact
timeline, adapt its presentation, and explicitly graduate to the existing
fully-declared Chrona resources. The work is design-only: it must establish
one canonical path before any schema, CLI, editor, or renderer implementation.

## Established constraints

* Project v0.5, View v0.8, Theme v0.3, Color Scheme v0.1, Layout Profile
  v0.3, and Render Context v0.8 are the current explicit canonical resources.
* `chrona render` is a Draft ingress for those already explicit resources;
  `render-review` is the immutable Context closure route. Neither is a compact
  authoring model or a preset resolver.
* Application Architecture requires every CLI, GUI, automation, and AI
  mutation to traverse Command Engine and forbids persisted Scene geometry.
* The closure resolver validates one exact schema/resource graph before any
  derived schedule, View, Layout, Scene, or renderer work. A facade cannot
  create a second parser or a renderer-local fallback.

## Design questions

1. Define the compact document, presentation binding, preset package, and
   resolved binding identities; decide their schema/version lifecycle and
   which are durable authored resources versus derived normalization records.
2. Specify exact Stage 1, Stage 2, and Stage 3 state transitions, precedence,
   diagnostics, provenance, version pinning/upgrades, and reproducibility
   boundaries.
3. Define the Authoring Normalizer and Preset Registry without allowing either
   to own Project semantics, scheduling, View geometry, Theme tokens, or
   renderer behavior.
4. Map CLI/GUI/AI interactions to typed Command transactions and define
   materialization, undo/redo, failure atomicity, Git diffs, and migration of
   existing explicit resources.
5. Determine how a compact source reaches the existing draft and immutable
   render routes without writing hidden resources or conflating draft output
   with revision-bound evidence.
6. Complete use cases, quality invariants, acceptance matrix, implementation
   slice boundaries, and #148's dependency boundary.

## Required design deliverables

The design review will publish:

* a canonical ownership/data-flow diagram and rejection of parallel models;
* schemas/resource inventory and strict version/migration decision;
* compact syntax and normalization law; preset resolution/override grammar;
* all three stage transitions and command/provenance contracts;
* a whole-architecture review against Project → Scheduler → View → Layout →
  Scene → renderer, closure, Command Engine, extension lifecycle, and draft
  rendering;
* new use-case definitions and an acceptance/implementation-slice matrix.

## Non-goals

No terse convenience syntax implementation (#148), GUI/editor, external
import/synchronization, implicit preset update, compatibility parser, or
renderer-specific authoring route is authorized by this design phase.
