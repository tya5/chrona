# Presentation Prefer-ladders

**Status:** Accepted
**Depends on:** [06 View Model](06-view-model.md), [08 Scene and Rendering](08-scene-and-rendering.md), [11 Extension Model](11-extension-model.md), [49 Semantic Presentation Contract](49-semantic-presentation-contract.md), [50 Constraint-driven Gantt Surface Quality](50-constraint-driven-gantt-surface-quality.md)
**Owns:** bounded authored placement preferences and their Layout decision record.

## 1. Purpose and boundary

A View may express a logical preference for an eligible label or callout.  It
does not express a coordinate, bounds, route, primitive, renderer command, or
new visual semantic.  Layout evaluates that preference against the completed
surface constraints and records the deterministic result; Scene projects only
that completed result.

The current View vocabulary is closed:

| Intent | Values | Eligible output |
| --- | --- | --- |
| `label.side` | `above`, `below`, `start`, `end`, `inside` | member label |
| `callout.placement` | `above`, `below`, `start`, `end`, `rail` | anchored annotation/callout |
| `text.wrap` | `allow`, `forbid` | the associated label or callout text |

Item intent takes precedence over row intent.  An explicit side or placement
is prepended to the applicable View fallback ladder without duplicating a
rung.  The ladder itself is ordered, finite, and may end in `suppress`.

## 2. Layout decision contract

For each eligible request Layout owns measurement, candidate geometry,
collision/viewport checks, wrapping, and the first feasible rung.  The typed
`PlacementDecision` records the stable request identity, source reference,
requested ladder, selected rung, and outcome.  A placed decision selects a
rung from its requested ladder; a suppressed decision selects the terminal
`suppress` rung.  An exhausted ladder without that terminal policy diagnoses.

Completed `TextPlacement` and associated annotation box/leader placements
carry the geometry used by Scene.  Scene must neither receive raw View intent
nor retry a rung, measure text, select a label host, or route a leader.

## 3. Extension boundary

The semantic registry is a closed host-owned mapping from known semantic IDs to
Scene and Theme roles.  A Project profile package is a domain-schema package;
it is not a presentation registry.  Therefore a profile package cannot add
`presentationExtensions`, a new column source, a primitive kind, a Scene role,
or renderer-local geometry merely by declaring YAML.

Adding a new standard presentation meaning is a host feature: it changes the
versioned Scene vocabulary, supplies a semantic-registry binding and Theme
contract, and defines Layout eligibility before exposing View syntax.  Trusted
renderer code plugins remain separately governed by the Extension Model and
can only implement existing completed Scene semantics.  There is no dynamic
presentation-extension registration path in the current profile.

## 4. Architecture consistency

```text
Project facts + View intent -> normalized projection -> Layout decisions/geometry
                                                   -> Scene primitive projection
                                                   -> target adapter
```

This keeps Project/profile packages semantic, View declarative, Layout
geometric, Scene renderer-neutral, and adapters serializing.  It deliberately
rejects a second presentation-package authority and any renderer fallback.

## 5. Non-goals

This contract does not add relation-route ladders, table allocation policy,
arbitrary expressions, dynamic semantic packages, raw SVG, or coordinate
authoring.  Each would need its own typed vocabulary and boundary review.
