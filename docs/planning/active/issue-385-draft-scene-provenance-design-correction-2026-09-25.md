# Design Correction: Draft Scene Provenance (#385)

**Status:** Accepted correction to the Published Inspection Scene design.

## Finding

An immutable render has a persisted Render Context identity.  A Draft render
does not: its Context is an in-memory ingress adapter whose revision/content
identity sentinel is `draft`.  Serializing that synthetic envelope as a
resource with an SHA-256 content identity would falsely claim an immutable
artifact and violates the public Scene identity schema.

## Corrected provenance rule

* An **immutable** Scene includes the resolved Render Context and every
  closure resource, each with its immutable SHA-256 identity.
* A **draft** Scene includes only the actual explicitly loaded Draft
  resources, each with the SHA-256 identity computed from its source bytes.
  It does not include the synthetic `draft-render` Context as a resource.
* `provenance.mode` makes this difference explicit.  A Draft Scene remains
  useful inspection evidence but is not materializer evidence and cannot be
  replayed as a Context.

## Architecture review

This correction preserves the distinction between a Draft ingress adapter and
an immutable closure.  It neither weakens the content-identity format nor
creates a fake Context resource.  The serializer only reports identities that
the closure actually verifies; no target adapter, materializer, or authoring
authority changes.
