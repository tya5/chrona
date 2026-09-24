# Design Correction: Provider Context Synchronizer (#380)

**Decision:** Accept correction before implementation resumes.

The provider build correctly changes checked-in font and metric identities. A
Render Context pins those identities, but the public materializer is a closure
consumer: it must reject stale identities and cannot rewrite authored Context
source. Requiring a human to copy identity records would create an unreviewed
second writer and contradict the generated-evidence policy.

The added offline synchronizer is therefore a build-time ownership boundary.
It copies one validated provider descriptor into the `fontMetrics` field of one
validated Context and preserves every other Context field. Runtime resolution,
Layout, Scene, adapters, and materialization do not import it. After
synchronization, the existing public materializer remains the sole SVG writer
and the existing Context parser remains the authority that verifies the result.
