# Implementation Amendment — Theme Inheritance Source Identity (#378 I378-2)

**Design correction:**
`issue-378-theme-inheritance-source-identity-correction-2026-09-26.md`.

## A378-1 — Correct the derived source contract and Draft resolver

Require `sourceContentIdentity` alongside canonical `contentIdentity` in the
v0.12 schema. Refactor the resolver around an explicit source loader that
returns decoded data plus its byte identity. Verify source identity before
recursive semantic resolution, verify canonical identity after it, and retain
the existing raw-byte identity for ordinary v0.11 Draft Themes.

**Acceptance:** independent tests prove source-byte mismatch, canonical
mismatch, unknown override, recursive base, and ordinary v0.11 identity
semantics.

## A378-2 — Connect immutable Context through the same resolver

Have Context Theme loading create only safe, same-store, same-revision sibling
references. Give their declared `sourceContentIdentity` to `SnapshotReader`,
then use the shared resolver to validate canonical effective identity and
return the ordinary effective Theme source. Do not add inheritance state to
RenderClosure, Layout, Scene, or materializers.

**Acceptance:** equivalent Draft and snapshot fixtures yield byte-equal
effective Theme values and equal effective identity; a wrong source pin and a
wrong canonical pin fail at their distinct boundaries.

## A378-3 — Complete the tutorial and release evidence

Update the compact base/derived Theme fixture and guide to show both pins.
Run resolver, Draft/Context closure, and focused rendering tests. Then run
conformance and public materializer checks, inspect the batched generated SVG
diff, and publish the I378-2 acceptance review.

**Acceptance:** two documented Theme overrides visibly materialize, Context
closure remains reproducible, and generated evidence has no unintended diff.
