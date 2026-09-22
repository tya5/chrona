# Issue 136 Scenario Overlays Design Plan

## Objective

Define a named, reviewable what-if state inside one Project without copying a
Project file, changing scheduler semantics, or creating a second presentation
pipeline.  The result must enter the existing Snapshot comparison path as a
derived scheduled Project while retaining distinct provenance from a Snapshot.

## Authoritative starting facts

- `timeline/v0.4` is the current Project contract.  It owns semantic object and
  relation data; it has no scenario syntax.
- `chrona/view/v0.6` owns comparison selection.  Its baseline is currently
  `primary | snapshot`; explicit rows admit `primary | snapshot | actual`.
- Render Closure resolves an immutable primary Project and, when declared, an
  immutable `snapshot-ref` and its separately pinned Project.  `render_review`
  schedules both before creating `ReviewProjection`.
- Layout owns all geometry and Scene only projects completed placements.  The
  existing `snapshot` semantic, role, and comparison track are sufficient for
  a scenario overlay.

## Design work

1. Complete an ownership and invariant review across Project Format (persistent
   scenario syntax and merge law), View Model (selection and explicit-row
   source), Presentation Format/closure (evidence identity), Scheduling Model
   (derived input boundary), Application Architecture (one resolver), Quality
   (determinism and diagnostics), and the use-case catalog.
2. Decide and document the successor contracts:
   - named scenarios are Project-owned maps of object and relation overrides;
   - recursive mappings merge, scalar/list values replace, and `null` deletes;
   - scenarios may alter objects and relations but never the Project frame
     (project identity, calendars, entities, or extensions);
   - automatic comparison selects one scenario baseline; explicit rows may
     select named scenario items; Snapshot remains an immutable historical
     state and is never normalized into a scenario.
3. Specify a typed, deterministic scenario resolver.  It produces a derived
   Project value before the unchanged scheduler runs; it neither publishes a
   resource nor mutates the closure's primary Project.  Resolver diagnostics
   must identify the scenario and authored path.
4. Specify evidence provenance.  A rendered scenario must expose the resolved
   scenario id/title through View-owned table/summary facts and an immutable
   closure identity record, without changing Scene geometry or renderer
   behavior.
5. Review the design against the Project → View → Layout → Scene → Renderer
   architecture and explicitly reject any alternative that introduces scenario
   logic into Layout, Scene, a renderer, or a scheduler.

## Planned publication units

1. This design plan.
2. A complete English design and architecture-consistency review, including
   version/migration decisions and acceptance scenarios.
3. An implementation plan with independently mergeable contract/resolution,
   View/provenance, and example/acceptance slices.
4. Only then, implementation slices with focused tests, full pytest, public
   materializer checks, generated-output review, CI, and serial merges.

## Acceptance for the design phase

- Every new concept has exactly one owner and no persistent Scene geometry.
- Scenario, Snapshot, Actual, and primary-plan provenance have non-overlapping
  meanings and stable identity rules.
- The merge law, frame restriction, validation surface, and diagnostics are
  testable without relying on implementation accidents.
- A Scenario reaches the existing comparison pipeline as a scheduled derived
  Project; no new renderer or Layout behavior is required.
- Migration is deliberately versioned.  Compatibility that would preserve an
  ambiguous contract is not retained.
