# Issue 254 Advanced-Contract Example Design Plan

## Purpose

Add one public HALCYON materialization that exercises released Project and
View contracts together, so the existing byte-reproduction and
output-property gates detect real cross-boundary regressions rather than only
unit-level regressions.

## Discovery questions

1. Identify a small connected HALCYON subtree that can demonstrate hierarchy,
   WBS, planned progress, typed object links, scenario comparison, critical
   relations, and total float without turning the example into a contract dump.
2. Verify that scenario primary/baseline data and hierarchy rollups compose in
   one View without injecting geometry or renderer-specific fields into Project
   or View.
3. Determine whether any existing View/Scene assertion is insufficient to
   prove link anchors, WBS/float cells, scenario provenance, and critical-edge
   semantics in a public SVG.
4. Define the generated-artifact delta so only the new slide is introduced;
   existing HALCYON evidence must remain byte-identical.

## Design deliverable

The design review will specify the exact authored Project additions, View
selection/grouping/columns/comparison policy, Layout/Theme reuse, Context and
manifest registration, and each acceptance assertion. It will explicitly map
responsibilities as Project facts → View selection/presentation → Layout
placement → Scene semantics → generic SVG serialization.

## Non-goals

This issue does not add a new authoring vocabulary, scheduling policy,
renderer capability, or test-only bypass. A missing contract or ownership
boundary found during investigation returns to a separate design correction.
