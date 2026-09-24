# Implementation Plan: Overlay corpus evidence (#382)

**Status:** Accepted.

**Implements:** [Overlay corpus evidence design](../../design/issue-382-overlay-corpus-evidence-design-2026-09-25.md)

## I382-1 — Author the current overlay Context closure

Add `layouts/overlay-briefing.yaml` and `contexts/11-overlay-briefing.yaml` to
HALCYON.  The layout uses only current v0.4 syntax and existing semantic slot
sources; its overlay root declares a guide, barrier, and anchored children.
Append one manifest slide with declared SVG and Scene artifact paths.

**Acceptance:** strict current schema and Context closure validation succeed;
the Layout resolver accepts reference scope, tokens, and acyclic ordering.

## I382-2 — Prove solver and materializer evidence

Add a focused test over the real overlay layout that asserts guide and barrier
coordinates, anchor gap, and determined decisions.  Generate the two artifacts
only through the public materializer; add Scene/slot assertions if the existing
materializer tests do not already cover the new slide.

**Acceptance:** the source facts and completed user-facing evidence agree; all
materializer byte checks pass with no hand-authored output.

## I382-3 — Publish curation disposition and release

Regenerate the presentation coverage report; revise `programme-at-scale`'s
deferred blocker to state the remaining responsive-comparison need.  Regenerate
gallery pages, review artifacts, run focused tests, public materializers,
conformance, full pytest, structural checks, wheel smoke, and three-platform
CI.  Publish an English acceptance review and close #382 after CI passes.

## Deliberate non-goals

* No merge, rebase, resource copy, or compatibility adaptation from #272/#283.
* No new responsive View/Layout feature or `programme-at-scale` gallery set.
* No coverage threshold or SVG parsing.
