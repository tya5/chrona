# Design Plan: Presentation vocabulary coverage (#375)

**Status:** Accepted.

## Context

The semantic corpus report deliberately excludes presentation contracts.  The
published `scene-v0.1` boundary now supplies completed placement/primitive
evidence, so a new report can measure presentation declaration and realized
output without parsing SVG or importing Scene/Layout builders.  The original
issue names superseded v0.12/v0.5 schemas; the design must instead use the
live schema inventory at implementation time.

## Questions to resolve

1. What is the authoritative closure traversal from each declared manifest
   slide to View, Layout Profile, Theme, and Color Scheme resources?
2. How are finite schema values identified without treating open maps or
   conditional implementation details as vocabulary?
3. How will the report distinguish a value declared in an input resource,
   a Layout slot placed in a completed Scene, and a slot that emitted visible
   primitive content?
4. How can every declared slide supply checked-in Scene evidence while
   preserving materializer byte-reproduction discipline?
5. Which scope must remain outside this issue so that #382 consumes the
   report rather than being pre-implemented by it?

## Required design outputs

* An English design and architecture-alignment review defining the read-only
  tool boundary, report model, source of truth, and version policy.
* An implementation plan with independently reviewable discovery, coverage,
  corpus-evidence, and release slices.
* Explicit migration of all declared corpus slides to expected Scene evidence,
  if that is necessary to make realized-slot results complete.

## Guardrails

* The report is a deterministic curation selector, never a CI coverage
  threshold or authoring validation rule.
* Use serialized Scene documents for realized output; do not parse SVG
  `data-*` attributes and do not import Layout/Scene builder code.
* Do not retain stale schema-version pins merely because the issue body named
  them; resolve only schemas marked `live` by the public inventory.
* Do not add #382's overlay/guides/anchor/barrier corpus fixture here.
