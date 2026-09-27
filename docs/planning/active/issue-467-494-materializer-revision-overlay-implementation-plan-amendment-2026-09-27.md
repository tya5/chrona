# Implementation Plan Amendment — Local Revision Copies and Provider Overlay (#467, #494)

**Amends:** [L1 materializer context-integrity implementation amendment](issue-467-494-l1-materializer-context-integrity-implementation-plan-amendment-2026-09-27.md). **Design correction:** [revision-overlay correction](../../design/issue-467-494-materializer-revision-overlay-design-correction-2026-09-27.md). **Review:** [architecture review](../../reviews/current/issue-467-494-materializer-revision-overlay-architecture-review-2026-09-27.md). **Normative authority:** [Specification 40](../../specification/40-example-reproducibility-and-materialization.md), §2.

## M1 clarification

M1 has two physical staging rules under one unchanged logical identity contract:

| Authored source | Physical staging | Required identity behavior |
|---|---|---|
| Local reference | Declared revision-token directory plus authored address | Copy exact bytes; preserve opaque token/address; verify authored content identity when present. |
| Package/other provider-backed resource or asset | Transient namespace disjoint from revision/address paths | Key by full authored provider identity, address, resource revision where applicable, and authored content identity where present; stage and serve only verified exact bytes. |

The overlay is execution-only and is discarded with materialization. It must not impersonate a local reference, persist an alias, or permit fallback by address/token. This clarification resolves the Spec40/Spec50 interpretation conflict and changes neither the planned M1 ownership nor the later L1 migration boundary.

## M1 acceptance checks and publication gate

Retain all existing M1 tests and evidence. Add explicit checks that a local reference is copied at its own revision/address, that package/provider resources stage outside every canonical revision/address directory, and that equal addresses with different providers or revisions cannot cross-resolve. Verify full-key lookup, exact copied Context bytes, authored fields unchanged, identity verification before registration and on read, and fail-closed behavior for missing keys/resources, unsafe paths, stale identities, or staged-byte mutation. The implementation remains publishable only with the focused suite and public materializer evidence already named by the parent plan; this amendment supplies no passing-test or acceptance claim.

No product code is changed by this planning amendment. No schema migration, canonical-reference migration, or issue-acceptance change is required. Existing rendered artifact differences remain subject to the parent plan's byte-diff and public-output inspection gates.
