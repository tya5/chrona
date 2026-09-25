# Relation semantics design (#394, #395)

## Decision

A rendered relation is a completed Layout result derived from one typed
relation presentation fact: stable relation id, source/target object and
endpoint kinds, signed calendar-qualified lag, semantic class, and View label
policy. This replaces the current raw-relation reread in Layout and ensures
terminals, routing, labels, and diagnostics cannot disagree.

## Contracts

Theme v0.9 supersedes v0.8 with independent `relationSourceTerminal` and
`relationTargetTerminal` role treatments. Terminal shape is a closed finite
set: `triangle`, `open-triangle`, `chevron`, `circle`, and `open-circle`.
Each role owns its own geometry and fill/stroke mode; a circle is
non-directional and never inferred from endpoint kind.

View v0.15 supersedes v0.14. Its normalized `relations` object retains
`mode` and `overflow`, and adds an ordered `content` selection from
`lag` and `endpointPair`. The default is no labels. A `lag` label omits zero
lag; its text preserves sign and the declared unit/calendar provenance.

## Placement and Scene

Layout consumes typed relation facts, chooses ports from their endpoint kinds,
routes once, and emits a `RelationPlacement` containing completed source and
target marker geometry plus zero or one measured `TextPlacement`. It anchors
label candidates at stable route segments, collides against required marks,
text, boxes, and prior relation labels, and obeys existing relation overflow:
`suppress` records `W_LAYOUT_RELATION_LABEL_SUPPRESSED`; `diagnose` raises a
named Layout error. No renderer measures, chooses a segment, formats lag, or
selects a marker.

Scene v0.4 carries `markerStart` and `markerEnd` on a `Path`; the existing
singular target marker is removed rather than retained as compatibility state.
Scene source order stays canonical. SVG serializes completed `marker-start`
and `marker-end`; relation text is an ordinary completed text primitive.

## Architecture review

Project owns dependency facts; projection owns typed selection; Theme owns
terminal treatment; Layout owns routing, label measurement and suppression;
Scene owns completed geometry; adapters serialize only. This preserves
Specification 32 and Specification 50, avoids a second relation route in
Scene/SVG, and keeps the terminal/label vocabulary finite and coverage-auditable.

## Acceptance

Corpus evidence must show a non-directional terminal, an independently marked
source endpoint on a start-to-start relation, a positive calendar-qualified
lag label, and a negative lag label. It must demonstrate suppression or
diagnosis through a neutral fixture, regenerated public materializer bytes,
coverage, conformance, full tests, and three-platform CI.
