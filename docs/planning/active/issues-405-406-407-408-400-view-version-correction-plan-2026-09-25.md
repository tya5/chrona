# Design Correction Plan — Axis View Version (#405, #406, #407, #408, #400)

**Trigger:** The accepted design named View v0.16 as the axis migration target,
but v0.16 is already the live public runtime contract and retains the legacy
positional axis fields. Replacing it in place would make a published version
ambiguous.

1. Publish the corrected v0.17 migration decision and review it against the
   no-compatibility and closure contracts.
2. Amend I1 to add v0.17, remove v0.16 runtime ingress atomically, and migrate
   all public Views, Context closures, fixtures and inventory evidence together.
3. Resume the approved axis/failure implementation only after that publication.
