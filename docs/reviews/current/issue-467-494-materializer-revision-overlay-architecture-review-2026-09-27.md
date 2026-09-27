# Architecture Review — Materializer Revision Overlay (#467, #494)

**Reviews:** [revision-overlay design correction](../../design/issue-467-494-materializer-revision-overlay-design-correction-2026-09-27.md). **Amends:** [L1 materializer context-integrity review](issue-467-494-l1-materializer-context-integrity-architecture-review-2026-09-27.md). **Normative text:** [Specification 40](../../specification/40-example-reproducibility-and-materialization.md) and [Specification 50](../../specification/50-materializer-closure-integrity.md). **Inspected public base:** `origin/main` `d615bfb4f630f97fa4c4bb41b64b425a578d2ebb`; local M1 implementation inspected read-only in the isolated worktree.

## Finding and decision

Spec40 §2's physical-copy sentence conflicts with the approved Spec50 overlay clarification when read to include provider-backed package resources. The architecture resolves this by distinguishing logical identity from physical execution staging: local resources remain in their declared revision/address namespace; provider-backed resources may be staged in a disjoint transient overlay keyed by full authored identity. Accept this clarification. It preserves the immutability and reproducibility contracts without broadening the schema or weakening pin validation.

Read-only inspection of the current M1 materializer found local references copied to `snapshot_directory(snapshot, token)/address`; package references/assets use `materialized-overlay`, where staging filenames derive from hashes of full reference/asset keys. Overlay reads verify staged digest and expected identity. This is consistent with the selected rule. The worktree contains uncommitted implementation changes, so this is a design conformance observation, not an implementation acceptance or claim about published main.

## Whole-architecture consistency

| Area | Review |
|---|---|
| Spec15 / Revision Store | Revision tokens remain opaque identity. Overlay addressing uses authored identity and does not equate resources from token spelling or address alone. |
| Spec40 / example materialization | Local physical copies stay revision-scoped. Provider-backed staging is explicitly allowed only as transient, disjoint execution state. |
| Spec50 / authored closure | Authored Context bytes and references remain exact. Overlay bytes are verified; no overlay becomes a replacement Context or canonical resource. |
| Materializer and resolver | Own staging, verification, lookup, failure, and cleanup. Local snapshot reading and package provider resolution remain their existing source boundaries. |
| View, Theme, and Context | Authored resource pins remain unchanged. Context revision selects its local closure namespace; Theme identity continues to govern its own authored visual choice. |
| Layout, Scene, adapters | No new persistence/provider responsibility. Layout consumes resolved values; Scene carries completed output facts; adapters serialize them. |
| #467/#494 | No acceptance wording or evidence changes. Lane and route criteria remain unaccepted by this document. |

## Failure, compatibility, and disposition

Provider resolution failure, unsafe paths, content-identity mismatch, missing overlay keys, and mutated staged bytes fail closed through existing stable diagnostics. Same-address resources from different providers or revisions cannot satisfy one another. No schema migration or authored-data migration is required. Physical package staging changes only the temporary execution layout; exact Context hashing may still change reported digests relative to prior normalized serialization and generated artifact changes must be measured separately.

**Disposition:** approved for M1 implementation planning as a clarification to the existing overlay design. The matching Spec40 wording is updated, and the implementation amendment records the local/provider split. This review does not accept the implementation or close any issue criterion.
