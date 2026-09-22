# Issue 145 Network Layout-Closure Implementation Amendment

## Authority and reason

This amendment implements the decisions in
`issue-145-network-layout-closure-design-correction-2026-09-22.md`.  It
replaces the original single N145-3 implementation unit because the merged
N145-2 graph composer is not yet a complete measured placement closure.  The
split makes the correction independently testable before Scene and public
materialization consume it.

## Revised delivery order

### N145-3A — close typed network Layout

**Files and responsibilities**

* Extend Theme v0.3's closed metric vocabulary and public Themes with network
  node minima/rank-gap tokens.
* Add the unconditional neutral `network` entry to the render source catalogue
  and teach source measurement to retain per-node label measurements.  It must
  not select a surface or inspect raw relation mappings.
* Replace caller-supplied network node dimensions with Layout-owned dimensions
  derived from the resolved metrics and measured label runs.
* Extend `DependencyNetworkLayout` with complete text placements and make it
  apply the resolved writing mode, slot bounds, port, route, overflow, and
  placement-quality invariants.
* Make the Scene input validate surface-specific required source sets.  It may
  dispatch no Scene primitives in this slice.

**Acceptance**

1. A network layout has measured node labels, valid distinct ports and
   completed quality-checked routes without geometry calculated by Scene.
2. Horizontal and vertical rank direction are deterministic; cycles,
   unavailable endpoints, overflow, bad ports, and unrouteable required edges
   return stable diagnostics.
3. A table/timeline surface retains its existing required-source behaviour and
   byte-characterized output; a network surface rejects table/timeline-only
   required slot sets.
4. Focused Layout/source/contract tests, full pytest, conformance, import and
   reachability gates pass.  The staged-module entry for
   `dependency_network` is removed once its generic dispatch seam reaches it.

### N145-3B — Scene adapter and HALCYON release gate

**Files and responsibilities**

* Add registry bindings `networkNode`, `networkEdge`, and `criticalEdge`.
* Replace the temporary unsupported-surface guard with the small typed Scene
  dispatcher.  The network adapter consumes only N145-3A placement records and
  emits existing Rect/Text/Path primitives; the table/timeline adapter remains
  byte-compatible.
* Add the HALCYON network View, Layout Profile, Context and expected SVG.
  Register the materialization and add focused projection/semantic/structure
  tests plus public output-property evidence.

**Acceptance**

1. Scene has no font-metrics, route, rank, port-selection, or raw-relation
   access on the network path; its only semantic strings are registry ids.
2. A HALCYON dependency-network Context materializes deterministically through
   unchanged closure, use-case, and renderer entry points.  Its SVG contains
   node, network-edge, and critical-edge identities and reproduces from public
   inputs.
3. Existing public table/timeline SVGs remain byte-identical; generated SVG
   diffs contain only the new network materialization.
4. Focused tests, full pytest, conformance, output-property/materializer,
   generated-artifact diff, and architecture-boundary review all pass.

## Publication order

N145-3A and N145-3B are each a separate PR.  Before either merge, fetch
`origin/main`, inspect its exact range and PR check state, and merge serially.
No implementation starts until this amendment is merged.  A discovered
ownership drift returns to design review before implementation resumes.
