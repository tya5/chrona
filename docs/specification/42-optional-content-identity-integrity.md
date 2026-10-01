# Optional Content Identity Integrity Policy

**Status:** Design complete — Issue 44

## Policy

A resource reference MUST identify a Store, immutable revision, and address. `contentIdentity` is an optional exact-byte pin. When supplied it MUST match or fail with `E_CONTENT_IDENTITY`; when omitted, a reader that has been explicitly opted out computes the identity and carries it in the resolved closure/result.

## Store read path default (Issue #723)

The schema keeps `contentIdentity` optional, but the Store read path requires it by default. `LocalSnapshotReader`, `LocalBaselineRegistry` and a Store config that omits `integrity` all reject an omitted identity with `E_CONTENT_IDENTITY_REQUIRED`; a mismatch still fails with `E_CONTENT_IDENTITY`. An optional pin is not a limiter for what the reader will open, so omission is an explicit opt-out rather than the default: `require_content_identity=False` in code, `integrity: optional` in a Store config, `--allow-missing-content-identity` on the public CLI. `chrona init --example` writes `integrity: optional` with a comment, because the example Contexts leave inner references unpinned by design (ADR-0030) and the example corpus is not a trust boundary (Issue #727); the plain `chrona init` writes no Store config, and every other Store keeps `required`. `chrona render-review --store-config` reads a Context through that config, so its `integrity` applies.

## Mandatory pins

Extension packages always require `contentIdentity`. Commands and baseline operations preserve optimistic locking: a supplied `expectedContentIdentity` is verified; an omitted expectation relies on the immutable revision token. Result references always include a computed identity.

## Boundaries

Schemas permit omission. Readers compute identity. Closure/result artifacts expose computed identity. Examples may omit repetitive pins. No latest lookup, mutable tip, or weakening of package supply-chain verification is introduced.
