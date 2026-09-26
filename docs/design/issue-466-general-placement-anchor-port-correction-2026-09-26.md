# Design Correction — Annotation Leader Anchor Ports (#466)

**Predecessor:** [#466 general placement design](issue-466-general-placement-design-2026-09-26.md).
**Discovery:** while preparing shared-obstacle composer wiring, the current annotation leader source was found to be the center of a synthetic one-pixel anchor rectangle, sometimes inside its own mark. With the newly required mark obstacles, that would block a legitimate leader before it leaves its host.

## Corrected contract

An annotation retains its View-owned object/facet/endpoint anchor. Layout resolves that anchor to one completed mark and then to a boundary port for leader routing: `start` and `finish` use the mark's corresponding completed ports, `at` uses its point-glyph port, and `body` uses the nearest point on the mark outline toward the selected annotation box port with a deterministic side tie order (`end`, `start`, `above`, `below`). The box placement anchor may continue to use the mark-local reference rectangle for candidate ranking; only the connector's route source is the completed boundary port. This preserves the declared semantic target without making an interior mark crossing necessary.

The shared index may exempt only an explicitly registered port obstacle for the exact source/target route endpoint. It does not remove the entire host mark, every mark in a row, or every obstacle with the same object ID. A direct visible-overflow fallback may be diagonal; its exact stroked segment is registered in the same index for later annotations. A later connector must avoid it unless a specific endpoint-port exemption applies. The route decision records its resolved source/target port IDs. Scene receives only completed points and identity.

The `at` point-glyph port has a finite footprint: the route begins at the glyph's nearest boundary point in the direction of the annotation box, not its geometric center. An endpoint with no visible mark remains `E_PRESENTATION_ANCHOR_MISSING`; Layout must not silently attach to another source or a row midpoint. A leader whose bounded route has no acceptable path uses the existing visible direct fallback and warning, not an unrecorded collision.

No View/Theme/Project schema or annotation anchor spelling changes. Public annotation leader coordinates may change; every change is a Layout geometry correction and must be batch-reviewed in Scene/SVG evidence. Existing rail and side search order remains unchanged until the separate #466 candidate-grammar design is completed.
