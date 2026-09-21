# Optional Content Identity Integrity Policy

**Status:** Design complete — Issue 44

## Policy

A resource reference MUST identify a Store, immutable revision, and address. `contentIdentity` is an optional exact-byte pin. When supplied it MUST match or fail with `E_CONTENT_IDENTITY`; when omitted, the reader computes the identity and carries it in the resolved closure/result.

A Store may declare `integrity: required`; readers then reject an omitted identity with `E_CONTENT_IDENTITY_REQUIRED`. The public CLI may request the same strict mode.

## Mandatory pins

Extension packages always require `contentIdentity`. Commands and baseline operations preserve optimistic locking: a supplied `expectedContentIdentity` is verified; an omitted expectation relies on the immutable revision token. Result references always include a computed identity.

## Boundaries

Schemas permit omission. Readers compute identity. Closure/result artifacts expose computed identity. Examples may omit repetitive pins. No latest lookup, mutable tip, or weakening of package supply-chain verification is introduced.
