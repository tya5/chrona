# Relation semantics acceptance review (#394, #395)

## Decision

Accept the relation-terminal and relation-label implementation.  Theme v0.9,
View v0.15, and Scene v0.4 move together: no live reader accepts the
superseded Theme or View contracts, and Scene no longer carries a singular
relation marker.

## Architecture review

| Boundary | Accepted responsibility | Evidence |
| --- | --- | --- |
| Projection | Select immutable `RelationPresentationFact` values, including endpoint, signed lag, calendar provenance, and label content. | Typed normalization tests. |
| Theme | Select independent finite source and target terminal treatments. | Theme v0.9 schema and corpus roles. |
| Layout | Resolve terminal geometry, select ports, route once, measure and suppress/diagnose labels. | `RelationPlacement` carries both markers and completed label text. |
| Scene | Project completed relation paths and text only. | Builder has no router, font metric, or terminal-token lookup. |
| Adapter | Serialize `marker-start` and `marker-end` without geometry selection. | SVG focused tests and Scene v0.4 external adapter fixture. |

The implementation preserves the existing presentation layering: neither
Scene nor SVG measures a relation label, chooses a route segment, or derives a
terminal from an endpoint.  The ASCII `start->start` endpoint spelling is
intentional: it avoids adding an undeclared glyph requirement to every
portable font asset.

## Corpus evidence

* Controller Z Executive uses a circular `relationSourceTerminal`; its Scene
  contains independent `markerStart` and `markerEnd` geometry and a signed
  `-5wd [engineering-jp]` relation label.
* HALCYON TVAC Slip emits `+1wd [range]` labels from calendar-qualified lag
  facts.
* The default content selection remains empty; zero lag therefore never
  creates an implicit label.  Requested labels share the established relation
  overflow policy and record `W_LAYOUT_RELATION_LABEL_SUPPRESSED` when
  suppressed.

## Verification

* Focused contract, Scene/SVG, typed-content, external Scene-adapter, coverage,
  and public-materializer tests passed.
* Full suite: `792 passed, 19 skipped`.
* All 21 declared corpus slides were regenerated through the public
  materializer; its reproduction suite passed `24 passed`.
* Conformance, schema/annotation/reference inventory, diagnostic/declared-value
  inventory, vocabulary and coverage checks, documented commands, module
  reachability, Scene delivery, View dispatch, semantic registry reachability,
  import direction, and text encoding passed.

## Release disposition

The regenerated SVG and Scene JSON changes are intentional: they contain the
v0.4 public Scene version and the independently completed relation terminals.
No compatibility reader or singular-marker field remains live.  #394 and #395
are ready for publication and CI.
