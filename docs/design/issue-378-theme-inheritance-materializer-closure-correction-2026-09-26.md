# Design Correction — Derived Theme Materializer Closure (#378 I378-2)

## Missing closure edge

The published I378-2 design correctly requires an immutable Context reader to
load a derived Theme's pinned base from the same snapshot. The public example
materializer currently copies only resources directly referenced by a Context
and known nested snapshot/icon resources. A derived Theme's `extends` edge
would therefore be absent from the snapshot it creates, even when the author
source is present. Context resolution alone cannot repair that omission.

## Decision

The derived Theme `extends` source reference is an explicit closure edge. The
ingress module provides one safe child-reference constructor, used by both the
immutable resolver and the materializer closure copier. It derives the child
address from the parent's declared address and the safe relative `path`; it
copies the parent store and revision, sets kind `theme`, and uses the child's
`sourceContentIdentity` as the byte pin. No current-working-directory or
unversioned file discovery is allowed.

The materializer recursively copies each base source, checking exact source
bytes before writing it into the same revision snapshot. It tracks source
addresses to reject cycles and rejects path traversal before touching a file.
The immutable resolver recursively reads those same references through its
`SnapshotReader`, then checks each base's canonical effective
`contentIdentity`. Thus the materializer owns packaging of declared bytes,
the reader owns immutable byte integrity, and the Theme ingress resolver owns
effective semantic identity and whole-entry override semantics.

Draft resolution follows the same source-byte and canonical-base checks with
its local file loader. Both modes return the same complete v0.11 Theme and
canonical effective identity for a derived root. Ordinary v0.11 Theme source
identity retains its existing byte-based contract.

## Failure and release implications

Unsafe relative paths, missing source bytes, wrong source pin, wrong canonical
base pin, wrong base kind/id/version, cycle, and invalid effective Theme are
independent rejection classes. A mismatch never causes fallback to a host
file or a different snapshot revision.

An integration fixture must use the real public materializer path with a
derived Theme in a Context. It must prove that the copied snapshot contains
the base, the Context reader resolves it, and deleting or tampering with the
base is rejected. The resulting RenderClosure contains only the complete
effective Theme resource; source edges do not reach Layout, Scene, or output
adapters.
