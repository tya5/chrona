# Design Correction — Preserve Authored Context Identity During Materialization (#467, #494)

**Continues:** [L0 sequencing correction](issue-467-494-l0-gate-design-amendment-2026-09-27.md) and resolves the separate Spec 50 blocker identified in the published [L1 resource correction](issue-467-494-l1-current-project-revision-design-correction-2026-09-27.md). **Plan:** [design plan](../planning/active/issue-467-494-materializer-context-integrity-design-plan-2026-09-27.md). **Review:** [whole-architecture review](../reviews/current/issue-467-494-l1-materializer-context-integrity-architecture-review-2026-09-27.md). **Implementation amendment:** [L1 plan amendment](../planning/active/issue-467-494-l1-materializer-context-integrity-implementation-plan-amendment-2026-09-27.md).

## Decision

The authored Render Context is an immutable manifest, not a scratch document to rewrite for local execution. Materialization MUST retain and copy the exact Context byte sequence, report its digest, and leave the parsed Context and every nested reference/locator unchanged. Verified copied resources are made available through a transient, immutable execution overlay keyed by the full authored locator/reference identity. The overlay is passed to closure and asset resolvers; it is not serialized into the Context and does not become a new canonical reference.

The minimal renderer-facing shape is one `MaterializedResourceOverlay` (name illustrative) that exposes two read operations: `read_reference(reference)` for declared presentation resources and `resolve_asset(locator, expected_identity)` for font/icon bytes. Its immutable keys include provider, provider identity when present, address, revision token for resource references, and authored content identity when present. Materializer stages copied bytes in the temporary closure, verifies all declared identities before registration, and binds overlay entries to those staged files/bytes. Resolution first checks for an exact overlay key; a miss falls through only to the ordinary resolver for the original provider when that provider is explicitly usable in this execution. Materialization itself must resolve and pin all assets required by the selected render target, so an overlay miss for an asset declared and copied by that materialization is an error, not a fallback opportunity.

For the L1 materialization path, the overlay wraps `LocalSnapshotReader` for immutable presentation resources and provides the same verified asset-root behavior to font resolution. Package resources and package icon catalogs are copied under an overlay-owned temporary namespace that is disjoint from authored revision/address paths, preventing collisions with local resources that happen to use the same address. The overlay maps original references to those staged bytes; the original Context references remain package references. Locally authored resources remain pinned to their declared store/address/revision. This removes the current parsed-reference mutation for package icon catalogs. The default `render_review` asset root is selected from the Render Context identity revision, matching the transient Context resource namespace; the overlay resolves authored package font locators to staged bytes without changing their provider metadata. Layout receives completed font metrics and icon data through existing closure values; Scene and adapters remain independent of providers and host paths.

## Resolution and identity rules

1. Read authored Context bytes once; preserve those exact bytes at its copied address and compute the emitted local Context reference identity from them.
2. Parse only for validation and closure traversal. Never mutate the parsed object or any child reference. Do not YAML-serialize it as a substitute for authored bytes.
3. For each required resource/asset, resolve through its authored provider and address; reject unsafe addresses and unavailable providers using existing stable diagnostics.
4. Verify the declared content identity when present. Required font and raster-icon assets continue to require their schema-declared identity. A mismatch rejects before rendering. Do not backfill a missing optional identity or substitute a newer package resource.
5. Copy verified bytes into an isolated temporary overlay namespace that cannot alias a canonical revision/address path. Register an overlay mapping only after the copied bytes' digest is verified. Overlay reads recheck the digest to detect accidental mutation during the render.
6. Resource-reference overlay keys include the immutable revision token, preventing bytes copied from one revision from satisfying another reference. Asset locator keys include provider identity and exact address; expected digest participates whenever authored.
7. The output/provenance record may report unchanged Context identity and resolved byte digests separately. It is not fed back as a replacement Context and cannot repair a stale pin.

The overlay is execution state with the lifetime of one materialization. It is discarded with its temporary directory. It is neither persisted as canonical data nor shared across invocations by mutable alias. Content-addressed caching is outside this correction.

## Failure behavior

- Authored resource identity mismatch: existing `E_CONTENT_IDENTITY`/reader identity diagnostic.
- Missing or malformed reference, unsafe path, provider unavailable, or missing copied file: existing materializer/revision-store diagnostic (`E_MATERIALIZER_CONTEXT`, `E_MATERIALIZER_PATH`, package/provider/reader diagnostic as applicable); do not search an unpinned location.
- Required font metric/font identity mismatch or unavailable bytes: existing `E_MATERIALIZER_FONT_IDENTITY` / `E_MATERIALIZER_FONT` family of diagnostics; keep stable codes unless implementation review demonstrates an existing code is semantically wrong.
- Raster icon identity mismatch or missing bytes: existing `E_ICON_ASSET_IDENTITY` / `E_ICON_ASSET_MISSING` closure diagnostics.
- Overlay key miss for a required declared asset: fail closed with the corresponding stable resource/font/icon missing diagnostic. Never infer a Theme revision, rewrite a locator, use a local package copy unrelated to its pin, or fall back to system fonts.
- Invalid Context shape remains the current materializer/schema failure. `--check` and `--write` share validation; `--write` replaces declared generated artifacts only after closure verification and successful rendering.

## Migration and compatibility

No Render Context schema version or canonical locator shape changes. Existing contexts remain authored as before. The materializer's emitted Context digest changes from a digest of normalized/re-written YAML to the digest of exact source bytes; for current source YAML that may change the reported digest even when semantic fields do not. Generated SVG/Scene bytes may remain stable, but this must be measured rather than assumed. Package icon-catalog Context references are no longer converted to local references in the parsed Context. Existing callers that relied on returned mutated Context data must instead consume the execution overlay, an intentional internal API migration.

The L1 Project update remains separate: update only `avionics-bustest.lag` from `2wd` to `4wd`, use the exact Project digest, pin that Project in all 15 Contexts, leave Theme refs at v1, and preserve Actual/frozen June baseline bytes. With Project/Context revision `example-v2` and Theme `example-v1`, font assets and copied Context use Context identity while the Theme remains unchanged. The independent Context-root selector correction was published at `04a35200`; this integrity correction does not reopen that ownership decision. Historical #498 I2 artifacts are not regenerated or relabeled.

## Boundaries and alternatives

- **Selected:** transient execution overlay. It preserves authored closure identity and avoids a schema change while allowing verified bytes to be local/offline and provider-independent during one render.
- **Rejected:** rewriting locators or references in parsed Context. It changes authored closure bytes and content identity, contrary to Spec 50.
- **Rejected:** editing package provider metadata to impersonate `context`. It confuses provider identity and can resolve the wrong asset.
- **Rejected:** asking each renderer adapter to resolve provider paths. That leaks persistence and host-resource concerns past completed Scene and violates adapter serialization responsibility.
- **Rejected:** permanent local aliases or fallback based only on address/token. Such aliases can bind bytes from a different revision/provider and weaken immutable identity.

The overlay belongs at resource access boundaries in materializer/use-case and resolver plumbing. Layout owns measurement/placement after font metrics are resolved; Scene carries completed marks and icon payload semantics; adapters serialize completed Scene. No new provider lookup is added to Layout, Scene, or SVG/PDF/PNG adapters.

## Acceptance evidence for the correction

For a corpus-wide focused suite, hash each original Context before and after, assert the copied Context file is byte-identical and the returned content identity matches that hash, and assert parsed Context/font/icon reference values are unchanged. Verify package and local asset positive paths, digest mismatch, missing file, stale revision/resource identity, overlay cross-key isolation, repeated byte-identical output, divergent Context/Project and Theme revisions, SVG font metrics, font-file targets, and PNG/PDF asset consumers where supported. Materialize all 15 HALCYON contexts through the public CLI; inspect complete Scene/SVG diffs. The L1 correction is publishable only after each public materializer succeeds and generated changes are explained.

This document does not satisfy any literal #467/#494 lane/route criterion; those exact rows remain in the linked design plan and implementation plan.
