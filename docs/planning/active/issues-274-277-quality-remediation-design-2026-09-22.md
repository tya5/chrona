# Issues 274–277 Quality Remediation Design

## Scope and order

This plan addresses the five reported defects without moving semantic decisions into
Scene or renderer code: #274 cross-region text collisions; #275 driving critical
relations; #276 missing Theme metric diagnostics and object-type selection; and #277
two-level axis hierarchy. The merge order is #274, the diagnostic half of #276, the
shared #275/#276/#277 design, then independent reviewed implementation slices.

## Boundaries

* Layout quality compares all required non-suppressed text placements. A collision
  region remains diagnostic context only; it is never an exemption. Explicit authored
  overlap requires a future typed placement policy, not an identifier accident.
* Scheduler analysis owns a deterministic `driving_relations` identity set. A relation
  is driving when its scheduled source endpoint plus its declared lag equals the target
  endpoint. View's `relations: critical` selects this analysis set; it does not infer
  a chain from per-object float.
* View selection distinguishes geometry kind (`span`/`point`) from Project object type
  (`task`, `gate`, `phase`, etc.). Include/exclude predicates are intersected
  deterministically before grouping and row construction; existing declarations retain
  their geometry-kind meaning.
* A missing `timeline.groupHeader.blockSize` is a Theme contract error with the metric
  pointer. Capacity after a resolved metric remains a Layout overflow error.
* Layout owns two-level axis geometry: coarse interval rectangles, centred-if-fitting
  coarse labels, per-level grid classification, and plot-only grid extents. Scene only
  projects typed placements; Theme resolves the existing axis-band/major/minor roles.

## Acceptance

Each slice supplies focused regression fixtures plus full-suite, conformance, public
materializer and SVG-diff review. The five changes must preserve ordinary explicit
View, Scheduler, Layout, Scene and renderer boundaries and introduce no Scene source
coordinates or renderer-local policy.
