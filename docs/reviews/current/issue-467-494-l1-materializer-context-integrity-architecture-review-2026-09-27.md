# Architecture Review — L1 Materializer Context Integrity (#467, #494)

**Reviews:** [design correction](../../design/issue-467-494-l1-materializer-context-integrity-design-correction-2026-09-27.md). **Plan:** [design plan](../../planning/active/issue-467-494-materializer-context-integrity-design-plan-2026-09-27.md) and [implementation amendment](../../planning/active/issue-467-494-l1-materializer-context-integrity-implementation-plan-amendment-2026-09-27.md). **Base inspected:** fetched `origin/main` `e96e8c134b472887ecf1db5c200744f75ce7e211`; Context-root correction `04a35200` was published during this design phase and does not change the materializer violation.

## Decision

The transient immutable resource overlay is consistent with the architecture and resolves the exact Spec 50 violation without a Render Context schema change. Accept for implementation planning. Materializer must preserve exact authored Context bytes and original parsed font/icon/reference fields; it stages verified copies and supplies them through resolver plumbing keyed by full immutable identity. No lane acceptance or implementation completion is claimed.

## Evidence from the current base

- Spec 15 §§2 and 6 define opaque revision identity and content identities for reproducible evaluation; matching an address/token alone cannot identify bytes.
- Spec 40 §§1–3 treats contexts as immutable closure manifests, requires references to be copied at declared revisions, and requires authored content identities to remain unchanged.
- Spec 50 §1 directly requires exact Context bytes, no YAML reserialization, and no parsed font metadata mutation; §§2, 3, and 6 distinguish provenance from authored authority and require fail-closed identity checks.
- `copy_context_closure` currently parses the Context, copies resources, rewrites package icon references and font locators, then `safe_dump`s the modified mapping. Its returned identity hashes these changed bytes.
- Current HALCYON corpus has 15 Context files. Each declares three font metric JSON locators and three font-file locators (Noto Sans Mono regular, Noto Sans regular, and Noto Sans bold), all package-provided and content-pinned. `15-gallery-image-notes` also declares an icon catalog; its current reference is local. The existing font content identities are explicit.
- At the inspected base, the renderer chose the asset root using Theme revision while `copy_context_closure` returned a Context revision equal to Project revision. Commit `04a35200` corrected the renderer to use Context identity and added the divergent-token regression. The authored-Context integrity problem remains.
- `LocalSnapshotReader` accepts only local store references and verifies declared resource digests. Font resource resolution currently supports `context` local assets and registered `package` providers. `resolve_render_context` already accepts decoded resource payloads for catalogs, and `_load_icon_assets` reads selected raster bytes through the snapshot reader. Overlay integration should therefore occur at reader/font-resource boundaries, not in Layout or adapters.

## Whole-architecture consistency

| Contract / layer | Finding |
|---|---|
| Specification 15 / revision stores | Preserved: the overlay key is based on complete authored identity, including resource revision; content bytes are checked against pins and tokens stay opaque. |
| Specifications 40 and 50 / authored closure | Preserved: exact Context bytes/hash are copied; the execution overlay is derived transient state and does not rewrite or replace authored closure. |
| Materializer / use-case | Owns staging, verification, overlay construction, lifetime, and provenance. No persistent alias or canonical data mutation. |
| Resource/font/icon resolver | Owns translating an authored immutable locator/reference to its verified transient copy. Lookup fails closed on key mismatch or absent required bytes. |
| View / Theme / Context | Their authored fields and references remain unchanged. Context identity determines its local closure namespace; Theme continues to own selected visual/font family. |
| Layout / Scene | Layout consumes resolved measurements and geometry only. Scene carries completed geometry and icon payload semantics; no provider/path access. |
| Output adapters | Continue serializing completed Scene only; no new asset-resolution responsibility. |
| #467/#494 | No issue criterion changes. Scheduler/project migration remains preparatory; lane/route acceptance remains for later implementation/evidence slices. |

## Failure and migration review

The correction fails stale resource or asset identity before render, distinguishes missing/unsafe/provider failures through stable existing diagnostics, and prohibits fallback to latest package/local bytes. It preserves optional missing identities instead of backfilling them. L1 Project `contentIdentity` pin remains checked against exact local bytes. The emitted Context content identity will now hash original source YAML bytes rather than normalized serialization, so closure provenance and potentially generated evidence digests must be regenerated and reviewed. SVG/Scene equality is a testable possibility, not an assumption.

Scope is suitable as an independent generic materializer slice followed by L1 corpus migration/output regeneration. This is larger than a one-line `render_review` root correction because the existing materializer violates normative closure identity for fonts and packaged icons; keeping it as a separate required prerequisite makes that scope explicit. It does not require a permanent overlay format or a general persistent cache.

## Review questions to settle during implementation planning

1. Use an explicit resolver/reader wrapper or pass a common protocol object to existing resource and font resolvers? Keep it transient and avoid broad public API changes.
2. Verify whether PDF paths and the CLI target-specific font key selection need separate positive tests; materializer currently copies metrics for SVG and both metrics/font for other targets.
3. Confirm root selection uses `RenderContextContract.identity.revision` and is stable when Context and Project tokens differ, with an explicit `request.asset_root` override retaining its current meaning.

These are implementation choices with a clear preferred answer: a small immutable resolver/reader wrapper at the current boundaries; target-specific verification for every supported materializer target; Context identity for the default root. No architecture issue remains unresolved.

**Disposition:** approved for implementation planning with the three questions above treated as focused implementation checks, not blockers. Current authored-context/materializer mismatch remains unresolved in code until the approved slices land and are reviewed. The issues remain open; no acceptance row is met by this document.
