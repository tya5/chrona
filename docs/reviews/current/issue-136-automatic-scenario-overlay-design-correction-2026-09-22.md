# Issue 136 Automatic Scenario Overlay Design Correction

For `comparison.baseline: scenario`, each automatic primary row MUST contain a
shared-track primary item and a shared-track selected Scenario item with the
same stable object id.  The table subject remains the primary item.  The
Scenario item uses source kind `scenario`, retains its Scenario id/provenance,
and is ordered after snapshot and before actual.  A missing object is a
comparison result, not a fabricated row.

This is View projection composition, not Layout/Scene behavior.  Layout sees
two completed members on the existing shared track; Scene uses existing planned
and snapshot-style comparison semantics.  Automatic mode resolves exactly one
selected Scenario.  Explicit mode remains the only route for multiple Scenario
hypotheses.  Acceptance requires an automatic row whose primary and Scenario
marks have distinct placements and stable source identities.
