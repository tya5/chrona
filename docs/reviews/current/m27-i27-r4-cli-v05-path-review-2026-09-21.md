# M27 I27-R4 CLI v0.5 Path Review — 2026-09-21

**Decision:** Complete after regression/conformance verification and publication.

`render-review` now normalizes table cells once, binds the current resolved closure
to `SceneBuildInput`, composes the completed v0.5 SceneSurface, and serializes it with
the v0.5 SVG adapter. The former reduced `scene.review`/`render_gantt` call is no
longer reachable from the public CLI path.

**Evidence:** CLI/context tests, full regression, and conformance.
