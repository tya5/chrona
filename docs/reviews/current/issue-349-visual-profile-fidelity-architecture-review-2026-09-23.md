# #349 Visual Profile Fidelity Architecture Review

**Decision:** accepted correction; implementation may begin after its plan is
published.

The correction removes a false universal-rich abstraction rather than teaching
the PDF adapter to silently approximate an SVG effect. Exact profile IDs make a
Context's declared target fidelity inspectable and give #350 an honest base for
future icon capability profiles.

Gradient endpoint composition belongs in Scene because it consumes completed
Layout bounds and Theme-selected angle, then produces renderer-neutral finite
geometry. This preserves the Layout → Scene → adapter direction. The adapter
serializes start/end points and cannot choose an angle convention.

Per-treatment fidelity avoids coupling an optional shadow to a required
gradient. The corrected diagnostics are resource-bound failures and retain the
role pointer through the use-case boundary. The draft render route remains an
ingress adapter: adding an explicit profile parameter creates no parallel
rendering pipeline.

The design deliberately limits the first gradient syntax to two stops. It does
not claim a non-authorable eight-stop model. SVG/PNG support is evidenced
separately; PDF remains baseline-only until it can preserve every claimed
capability. This is compatible with future icon catalogs because target
admission is a profile contract, not an SVG implementation detail.
