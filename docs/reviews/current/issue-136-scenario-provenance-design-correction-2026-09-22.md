# Issue 136 Scenario Provenance Design Correction

## Trigger

The S136-3 evidence review found that `resolve_scenario` computes
`ScenarioProvenance`, but the value is discarded before `RenderedReview` and
the materializer boundary.  An SVG can therefore show a derived hypothesis
without evidence of which hypothesis produced it.

## Decision

Scenario provenance is a completed application result, not a Scene attribute.
`RenderedReview` gains an immutable ordered tuple of Scenario provenance values
used for that render.  The render/materializer result serializes the same tuple
in its closure evidence beside the primary Project identity.  Each entry is
`scenarioId`, optional `title`, and derived `contentIdentity`; ordering is by
scenario id.  No coordinates, Layout choices, Scene primitive fields, or SVG
renderer rules carry this data.

`render_review` obtains provenance only from the pure resolver while building
the deterministic Scenario map.  It returns exactly the map entries actually
referenced by the View.  A no-Scenario render returns an empty tuple and retains
byte-identical existing SVG output.

The HALCYON Scenario fixture must assert both evidence contents and the visible
View-owned scenario table/summary fact.  The materializer test must demonstrate
that changing a selected Scenario changes its derived identity and that an
unselected Scenario does not enter evidence.

## Architecture review

This correction keeps semantic hypothesis/provenance at the Project →
application-result boundary.  View controls which hypothesis is requested;
Layout receives only scheduled projection facts; Scene projects completed
geometry; renderers remain target adapters.  It therefore restores the
evidence requirement without breaking the Layout/Scene seam.
