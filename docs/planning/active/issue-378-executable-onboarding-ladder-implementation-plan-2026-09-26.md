# Implementation Plan — Executable Onboarding Ladder (#378)

**Design:** `issue-378-executable-onboarding-ladder-design-2026-09-26.md`.
**Architecture review:**
`issue-378-executable-onboarding-ladder-architecture-review-2026-09-26.md`.

## I378-1 — Builtin preset catalogue and explicit copy command

Define a typed finite package catalogue; package the five complete ordinary
preset bundles; add an empty-output-only copy command; and link each id to
its gallery evidence.  Test safe selection, unknown id, output collision,
wheel installation, and draft rendering of every copied bundle against the
minimal starter.  Do not introduce network/package acquisition or gallery
resource lookup.

## I378-2 — Bounded Theme/View inheritance design and implementation

First publish the dedicated successor design for typed base references,
closure/identity, cycles, and Theme/View-specific override domains.  Implement
only the accepted finite vocabulary, with draft and immutable Context closure
tests.  Prove a five-line derived Theme overrides two tokens and produces a
visibly different Draft; reject unknown/deep/ambiguous overrides.  Do not
reuse guided-authoring overrides or generic YAML merging.

## I378-3 — Progressive tutorial and executable ladder gate

Create independent incremental Project fixtures and guide commands for every
literal learning concept.  Add a documented-command/evidence check that proves
the starter render, edit/re-render output change, every tutorial step, every
catalogue preset, and the derived Theme.  Cite corpus evidence rather than
copying its large sources.

## Release gate

Run focused schema/closure/CLI/tutorial tests; batch generated documentation
and review output once; run public materializer reproduction, conformance,
wheel smoke, and generated-document checks; review SVG differences; then
publish a literal #378 acceptance review.  Make one CI observation after the
final material commit.
