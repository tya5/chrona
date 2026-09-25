# Design Plan — Canonical Shared-Track Ordering and Summary-Bar Geometry (#417)

## Problem statement

The finite source-kind ordering used to traverse members on a shared track is
copied in Layout and Scene.  One Layout copy omits `scenario`, producing a
different order from all other passes.  The summary bar similarly derives its
height from an unowned division literal despite being a semantic mark.

## Required sequence

1. Inventory every shared-track traversal and identify whether it determines
   semantic source order, geometry, or adapter paint order.
2. Publish a design and architecture review assigning source-kind ordering to
   the model-level presentation policy, and summary-bar height to Theme.
3. Publish a bounded implementation plan with migration, characterization and
   public-materializer evidence gates.
4. Implement the policy once, make all traversal sites consume it, and replace
   the summary literal with the resolved Theme binding.
5. Run focused and complete tests, coverage/schema gates, materialization and
   generated-evidence review before publishing the implementation.

## Non-goals

This slice does not make source order author-configurable, conflate it with
Theme paint order, alter source/accessibility ordering, or add another track
type.  It does not change any mark's geometry other than the Theme-declared
summary-bar height.
