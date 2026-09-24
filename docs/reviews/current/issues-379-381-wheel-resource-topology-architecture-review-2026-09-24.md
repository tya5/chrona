# Issues #379 and #381 — Wheel Resource Topology Architecture Review

**Decision:** Accept design

| Boundary | Decision | Result |
| --- | --- | --- |
| Authored corpus → wheel | Hatch force-includes one authored source; no copied resource tree remains in `src/`. | Preserved |
| Resource lookup → init use case | `chrona.resources` resolves package/source topology; init consumes a named `Traversable`. | Preserved |
| Source development → installed wheel | The only source alternative is the declared importlib-resource development authority; a wheel does not discover a checkout. | Preserved |
| Smoke → resource API | Smoke uses public CLI journeys, not direct private resource reads or mock renderer behavior. | Preserved |
| Draft PNG → corpus evidence | PNG smoke is temporary Draft output; immutable Context/materializer evidence remains unchanged. | Preserved |
| CI → resource completeness | A finite reviewed matrix names each current resource tree and its observable proof. | Preserved |

The former duplicate made init correctness depend on synchronization rather
than ownership.  The proposed resolver follows an established schema pattern
without allowing use cases to inspect installation layout.  The smoke expansion
tests packaging at the same boundary users reach, including the two costly
trees previously never opened from a wheel.

Rejected alternatives are retaining a copy-and-sync gate, using `__file__` or
cwd checkout-path discovery, directly opening packaged files from smoke, and
rendering PNG with system-font fallback.  Each either creates a second
authority or fails to prove the installed product path.
