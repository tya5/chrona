# Architecture Review — Typed Table Allocation Closure (#403, #404)

**Decision:** Accept.

Normalizing View grammar at the review adapter prevents Layout and Scene from
inspecting schema-shaped maps. The measured ellipsis floor derives from Theme
typography, whereas a fixed numeric minimum would be undocumented policy.
Restricting shrink to declared flexible columns preserves `content` promises.
Named hierarchy selection removes source-order coupling without conflating
explicit-row nesting with Project hierarchy.

Acceptance requires typed ingress preservation; content/FR/fill/minmax,
diagnose/ellipsize, non-leading hierarchy, and alignment tests; Scene-boundary
tests; and regenerated public materializer evidence.
