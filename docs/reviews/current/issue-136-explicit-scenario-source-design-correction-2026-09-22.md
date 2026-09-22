# Issue 136 Explicit Scenario Source Design Correction

## Trigger

During S136-2 implementation, the proposed single `scenario_project` closure
value was found unable to meet the published explicit-row contract.  An
automatic View selects one baseline Scenario, but an explicit View may name
multiple Scenario ids in separate row items.  Resolving only the automatic
baseline would silently bind a row to the wrong hypothesis.

## Correction

The closure/application boundary resolves a deterministic mapping
`scenario_id -> (derived Project, schedule result, provenance)` for the union
of:

1. `comparison.scenario` when the automatic baseline is `scenario`; and
2. every explicit `rows.items[].source.scenario` whose kind is `scenario`.

The mapping is ordered by scenario id and each value is independently derived
from the same immutable primary Project.  `ReviewProjection` receives this
mapping and selects a scenario item by both source kind and scenario id.  A
`ReviewItem` carries the source Scenario id so Scene identity remains derived
from completed projection facts.  The View schema requires `source.scenario`
for kind `scenario` and rejects it for all other kinds.

Automatic row behavior is unchanged: it has at most one scenario baseline.
Snapshot remains separately pinned and may not be normalized into the mapping.
No Scenario map crosses into Layout, Scene, or a renderer.

## Consequences

- S136-2 implementation is paused before publication; the partial local work
  is not an accepted implementation state.
- The implementation plan's S136-2 acceptance must add two-scenario explicit
  row coverage and identity/provenance assertions.
- The corrected design is published and reviewed before code resumes.
