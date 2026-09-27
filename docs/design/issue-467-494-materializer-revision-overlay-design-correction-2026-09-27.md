# Design Correction — Revision Namespaces and Provider Overlays (#467, #494)

**Amends:** [L1 materializer context-integrity correction](issue-467-494-l1-materializer-context-integrity-design-correction-2026-09-27.md). **Normative authority:** [Specification 40](../specification/40-example-reproducibility-and-materialization.md), clarified with this correction. **Review:** [whole-architecture review](../reviews/current/issue-467-494-materializer-revision-overlay-architecture-review-2026-09-27.md). **Implementation plan:** [M1 plan amendment](../planning/active/issue-467-494-materializer-revision-overlay-implementation-plan-amendment-2026-09-27.md).

## Decision

The materialized resource's logical identity and its temporary physical location are separate. A locally authored reference MUST be copied under the directory selected by its own opaque revision token and its authored address. A package or other provider-backed resource MAY instead be staged in a transient execution overlay disjoint from canonical revision/address paths. Overlay lookup MUST use the complete authored reference or asset-locator identity, including provider and provider identity, address, resource revision where applicable, and authored content identity where present. The overlay serves the exact verified bytes resolved through that identity; it does not replace, normalize, or serialize a new canonical reference.

This is the explicit resolution of Spec40 §2's overly broad “every pinned reference” physical-path wording. The clause continues to prohibit moving revisions, primary-revision substitution, embedded schedule copying, and latest-resource resolution. Local references retain the revision namespace rule without exception. The transient overlay is limited to materialization execution and is discarded at its end.

## Identity, migration, and failure

There is no Render Context schema or canonical locator change. Existing authored provider/address/revision/content-identity values remain unchanged. Local closures continue using the declared revision namespace. Package/provider bytes now have a disjoint transient physical namespace; downstream code must resolve them through the identity-keyed overlay rather than infer location from an authored revision path. This is an implementation/storage-layout clarification, not a user-authored data migration. The Context copy remains byte-identical, and its reported identity is the hash of those exact bytes.

Before registering or returning staged bytes, materialization verifies any declared content identity. Missing providers or resources, unsafe addresses, stale or mismatched identities, an overlay key miss, or bytes that change after staging fail closed with the existing materializer, provider, reader, or identity diagnostic. No fallback to a different provider, local resource at the same address, moving revision, or host default is allowed. Logical revision tokens remain opaque and are not inferred from overlay paths.

## Ownership and scope

Materializer owns provider resolution, verified staging, overlay construction, and lifetime. Resolver/font/icon resource boundaries translate unchanged authored identities to staged bytes. Layout receives completed measurements and resolved visual inputs; Scene carries completed primitives and paint relations; adapters serialize Scene. No provider lookup or temporary-path knowledge enters Layout, Scene, or adapters. This correction changes no #467/#494 acceptance criterion and provides no lane/route acceptance evidence.
