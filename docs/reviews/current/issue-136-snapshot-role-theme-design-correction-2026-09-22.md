# Issue 136 Snapshot Role Theme Design Correction

## Trigger

The V136-2 HALCYON Scenario materialization reached SVG serialization and
failed with `E_THEME_ROLE_REQUIRED`.  Scenario correctly reuses the existing
Snapshot semantic binding, but the public HALCYON themes do not bind the
required `snapshot.fill` (and, where applicable, `snapshot.stroke`) tokens.
The prior assertion that the Snapshot role was already available was therefore
not true for materializable public themes.

## Decision

`snapshot` remains the semantic/visual role for both Snapshot and Scenario
planned marks.  It is not renamed to `planned`, and no Scenario-specific role
is introduced.  Every public materializable Theme must bind the color tokens
required by that existing role.  The binding intentionally gives historical or
hypothetical overlays a distinguishable neutral appearance while primary plan
continues to use `planned` and Actual continues to use `actual`.

Theme resources own that appearance declaration.  The semantic binding stays
in Scene; View chooses Scenario facts; Layout continues to place content
without inspecting the hypothesis; and the SVG renderer continues to resolve
only declared theme tokens.  A render that requests a Snapshot/Scenario role
without a corresponding Theme binding is a contract error, not a renderer
fallback opportunity.

## Release-gate amendment

Before adding the HALCYON Scenario SVG, update all current public HALCYON
themes with their Snapshot bindings and add a materialization test that proves
the Scenario context emits the Snapshot role successfully.  Regenerate only
the new Scenario artifact unless an existing artifact's bytes change for an
independently intended reason.

## Architecture consistency review

This correction completes an existing Style/Theme contract rather than moving
Scenario semantics downstream.  Project still owns the hypothesis, View owns
its selection and authored text, application code owns provenance, Layout owns
geometry, Scene maps a completed source kind to the established Snapshot role,
and renderers enforce token completeness.  The established layer boundaries
are preserved.
