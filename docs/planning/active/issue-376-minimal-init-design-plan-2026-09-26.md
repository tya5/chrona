# Design Plan — Minimal `chrona init` and Explicit Corpus Example (#376)

**Status:** In design.

## Problem statement

`chrona init` currently copies the HALCYON regression corpus, its materialized
evidence, and a local immutable Store closure.  It conflates two distinct
products: an editable first project and a pinned regression example.  #377 now
provides the missing draft-preset ingress and package-owned default required to
make a small project render without copied presentation contracts.

## Design questions

1. What files constitute the complete editable source of a first project when
   the draft default preset is package-owned?
2. Which `init` modes own source versus immutable Store state, and where may
   each place files?
3. How can the explicit HALCYON corpus example retain materializer capability
   without exposing generated revision closures as authored source?
4. Which documentation commands prove the smallest project and preserve the
   existing explicit-example workflow?

## Required evidence

- Inspect the current `initialize_project` application service, CLI parser,
  package-resource topology, Store discovery, and #377 draft resolver.
- Inspect the source and installed-resource behavior of the HALCYON template,
  especially Context references and snapshot paths.
- Confirm the public schemas needed for a two-task/one-gate Project and an
  Actual set; do not introduce an alternative Project syntax.
- Compare the result with the draft/evidence boundary: `render` may use a
  packaged default; `materialize` and immutable Contexts remain explicit and
  reproducible.

## Planned design deliverables

1. An English design that names the source/runtime boundary, default and
   explicit-example CLI semantics, template topology, diagnostics, and
   migration consequences.
2. A whole-architecture review covering package resources, draft ingress,
   Store authority, materialization, schema ownership, and documentation.
3. An implementation plan split into independently reviewable template/CLI,
   Store-topology, and documentation/evidence slices.  Any change that makes a
   copied example temporarily unmaterializable is atomic with its Store change.

## Non-goals

- Theme or View inheritance, preset library selection, package acquisition,
  guided-authoring changes, and terse Project syntax.
- Treating a draft render as immutable materializer evidence.
- Compatibility aliases for the old default corpus behavior.  The clean default
  is the intended public behavior; full corpus creation is explicit.

## Completion criteria

The design phase ends only after the architecture review accepts a source
template that a newcomer can read end-to-end, an explicit full-example path,
and a Store arrangement that never mistakes mutable source for an immutable
closure.  Implementation begins only from the resulting accepted plan.
