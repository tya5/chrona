# Issue 125 Presentation Flexibility Design

## Contract

View v0.4 replaces v0.3 atomically.  A row and an item may carry optional
`presentation.intent`: `label.side` is one of `above`, `below`, `start`, or
`end`; `callout.placement` is `above`, `below`, `start`, `end`, or `rail`; and
`text.wrap` is `allow` or `forbid`.  They are preferences only: coordinates,
sizes, routing, and collision rules remain outside View.  Item intent overrides
row intent; absent fields inherit View visibility defaults.

The View visibility contract gains ordered `fallback` arrays.  A label ladder
contains unique allowed sides followed optionally by `suppress`; relation and
annotation ladders contain their documented feasible placements followed
optionally by `suppress`.  `diagnose` remains the terminal policy when no rung
is feasible.  The author cannot use an empty ladder or repeat a rung.

## Ownership and evidence

Layout receives normalized intent and tries rungs in author order, testing the
same bounds, obstacle, and viewport conditions at every rung.  It emits the
first feasible placement or the explicit suppression/diagnostic result.  Each
chosen rung is recorded in the typed Layout manifest as placement identity,
requested ladder, selected rung, and outcome.  Scene only projects that result;
renderers never receive an intent or retry geometry.

## Extension seam

A profile package may declare `presentationExtensions` with a namespaced
semantic purpose and a namespaced column source.  The closure validates this
declaration with the package resource, rejects collisions with built-ins and
other package IDs, and resolves it into typed vocabulary before projection.
Extensions may contribute content facts and semantic registry entries but may
not add primitive kinds, renderer code, raw Layout coordinates, or a second
render pipeline.  Unrecognized extension declarations fail closure validation.

## Architecture consistency review

This preserves Project semantic ownership, View authoring ownership, Layout
geometry ownership, Scene primitive projection, and renderer serialization.
The fallback trace makes graceful degradation inspectable without admitting
manual pixels.  Package declarations remain immutable closure inputs, matching
the established profile boundary; they do not let extensions bypass schema or
semantic registry validation.

## Deferred scope

Native target-specific fallback, arbitrary expression columns, and extension
defined primitive/renderer implementations are explicitly deferred.  They
would cross the Layout/Scene/renderer seam and require a separate architecture
decision.
