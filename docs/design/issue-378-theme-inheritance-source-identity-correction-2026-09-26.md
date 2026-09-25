# Design Correction — Theme Inheritance Source Identity (#378 I378-2)

**Status:** Proposed for architecture review.

## Reason for correction

The accepted bounded-Theme design used one `extends.contentIdentity` both for
the base Theme's resolved canonical identity and for the immutable snapshot
reader's resource pin. Those are different representations: a snapshot reader
verifies the exact source bytes of the base resource, whereas the inheritance
resolver must verify the canonical identity of the complete, effective v0.11
Theme. One field cannot safely stand for both values.

This correction is required before immutable Context support is implemented.
It preserves the original finite override surface and does not expand
inheritance to Views or to generic YAML merging.

## Corrected source reference

A v0.12 Theme's `body.extends` has exactly these fields:

- `id`: the declared base Theme id;
- `path`: a safe relative path from the derived source to the base source;
- `sourceContentIdentity`: the SHA-256 identity of the exact base source
  bytes; and
- `contentIdentity`: the canonical identity of the base's resolved complete
  v0.11 Theme.

The identities have distinct duties and neither is optional. A Draft reader
loads the relative file, verifies `sourceContentIdentity` against its bytes,
then resolves and verifies `contentIdentity`. An immutable Context constructs
a sibling resource reference with the parent reference's store and revision,
the resolved relative address, and `sourceContentIdentity`; the snapshot reader
therefore retains its existing byte-integrity check. The resolver then checks
the loaded complete value against `contentIdentity`.

Each recursively derived base repeats this rule relative to its own source.
The resolver keeps a source-address stack for cycle detection. It never uses
the workstation filesystem for Context resolution, and it does not put source
references into the resulting RenderClosure.

## Effective identity and boundary

An ordinary v0.11 Theme retains its existing source-byte closure identity. A
v0.12 derived source becomes a detached v0.11 effective Theme and has that
effective document's canonical identity. This distinction avoids a
non-derived Theme silently changing closure identity merely because it passed
through the new resolver.

After source resolution, contract parsing, Layout, Scene, and all materializer
adapters see only the complete v0.11 Theme. The derived source form is an
ingress concern; its two pins are provenance and integrity data, not a runtime
inheritance edge.

## Rejection taxonomy

`E_THEME_INHERITANCE_SOURCE_IDENTITY` rejects a byte mismatch or a snapshot
base unavailable at its declared source pin. `E_THEME_INHERITANCE_BASE_IDENTITY`
continues to reject a canonical effective-base mismatch. Unsafe path, cycle,
base kind/version, schema, and unknown-override errors retain their existing
separate meanings.

## Migration

The unpublished v0.12 schema and Draft resolver are corrected atomically
before Context wiring. No public v0.12 document is migrated. The tutorial
fixture will include both pins explicitly, so authors can reproduce the
immutable form without relying on ambient file state.
