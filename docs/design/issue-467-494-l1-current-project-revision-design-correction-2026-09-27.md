# Design Correction — L1 Current Project Revision and Context Font Root (#467, #494)

**Corrects:** [L0 gate design amendment](issue-467-494-l0-gate-design-amendment-2026-09-27.md), which authorizes the L1 current-Project data correction but does not specify immutable identity or closure behavior. **Baseline:** published `origin/main` `c06daa954b5a240e21343fc0705a4d4aaf7095eb`. **Review:** [whole-architecture review](../reviews/current/issue-467-494-l1-current-project-revision-architecture-review-2026-09-27.md). **Plan:** [L1 implementation-plan amendment](../planning/active/issue-467-494-l1-current-project-revision-implementation-plan-amendment-2026-09-27.md).

## Decision

L1 changes only the current HALCYON-1 Project relation `avionics-bustest.lag` from `2wd` to `4wd`. The corrected Project bytes have SHA-256 `e196a21b0162e28d318f7e6512ada534cc1b6cdc35edb8fad6d84926bc4ca840`. The updated Project reference uses `example-v2`; the current corpus has one `project.yaml` path, so updating it replaces the previous source bytes in the working tree. Historical v1 bytes remain recoverable through their historical Git commit/captures, not as a parallel resource in the current checkout.

Each migrated Project reference MUST pin the exact Project `contentIdentity` (`sha256:e196a21b0162e28d318f7e6512ada534cc1b6cdc35edb8fad6d84926bc4ca840`). Render Context v0.16 permits this optional field and `_copy_reference` verifies it against the bytes it copies. This makes the single current local Project path checkable against the declared v2 bytes. All 15 references use this same digest.

`environment.fontMetrics` is Render Context-owned. `copy_context_closure` stages its Context-local font metrics and font files under the emitted Render Context token, which is the Project revision. `render_review` currently selects the immutable asset root from the Theme revision, which fails when Project and Theme tokens differ. Correct `render_review` to select `snapshot_directory(request.snapshot_root, render_closure.context.identity.revision)` (or the equivalent Context revision identity). Do not change materializer staging or migrate Theme references. The regression case is Project-v2/Theme-v1, with font assets present at Project-v2 and rendering resolving them from that Context root.

## Resource pins and history

All 15 HALCYON-1 Render Contexts move only `body.project.revision.token` to `example-v2` and add the exact Project `contentIdentity`. Their Theme references, bytes, and tokens remain unchanged at v1. Every other resource reference and the frozen `baseline-2027-06` identity remain unchanged. Actual observations and the frozen baseline bytes are unchanged.

The old examples' revision tokens alone did not make a mutable local path an immutable archive. The materializer reads the current local path and does not retrieve historical Project bytes by token. The #498 I2 Scene/SVG/PNG captures retain historical provenance and must not be rewritten or represented as output from the v2 Project. This L1 update does not add a local multi-revision store or a fallback.

## Ownership and normative review

Project owns the relation lag and scheduler-derived dates. Render Context owns the font metric declarations and its revision identity. The materializer owns copying declared resources and currently stages Context fonts under the emitted Context token. `render_review` owns selecting the Context-local asset root; it must use Context identity rather than infer a revision from Theme. Theme owns font selection, but Theme content and references are not changed. Layout and Scene consume resolved font metrics; adapters serialize completed geometry and provenance.

This root-selection change agrees with Specification 15 §§2, 6, 9 and Specification 40 §2: copied inputs are placed at their declared revision namespace, and consumers must read the right immutable closure. It does not require a normative change.

There is a separate existing conflict with Specification 50, which requires the authored Context file to be copied byte-for-byte and forbids rewriting its parsed font metadata. Current `copy_context_closure` rewrites font locators to `provider: context` and serializes the modified Context. This also conflicts with the exact closure boundary described in Specifications 38/40. That violation is outside the Context-root selection change and this document does not claim full Spec 50 compliance. Under existing materializer behavior, L1 may prepare the Project/scheduler correction, but its public materialization and generated-evidence acceptance cannot proceed. Treat the Spec 50 mismatch as an explicit blocker until a separate reviewed design/plan correction establishes a conformant materializer path; do not silently broaden this L1 slice to resolve it.

## Failure behavior and compatibility

If Project bytes do not match the pinned digest, materialization rejects. If a font asset is missing or its identity mismatches, materialization rejects under existing diagnostics. For equal Project and Theme tokens, the new Context-root lookup resolves the same location and should leave output byte-identical. For divergent tokens, the render-root correction uses the Context revision where assets are already staged. No Theme token is advanced to mask the defect.

The focused regression must demonstrate that Project-v2/Theme-v1 materializes font assets under Project-v2, that `render_review` resolves the assets from Context identity Project-v2, and that the rendered output succeeds without changing Theme. The materializer's Context reserialization remains an independently tracked blocker, so this regression alone does not establish L1 public materializer acceptance.

## Evidence boundary

L1 evidence must verify the Project digest in all 15 Contexts, unchanged Theme references, unchanged Actual and `baseline-2027-06`, the divergent-token root regression, scheduler date changes, and all changed outputs. The #498 I2 captures remain historical. Once the Spec 50 blocker is resolved, inspect SVG as well as Scene. No #467 or #494 lane acceptance criterion is changed or satisfied by this correction.

## Related records

- [L0 gate design amendment](issue-467-494-l0-gate-design-amendment-2026-09-27.md)
- [#498 I2 implementation-plan amendment](../planning/active/issue-498-bundled-default-readability-implementation-plan-amendment-2026-09-27.md)
- [Specification 15](../specification/15-revision-store-adapters.md), [Specification 40](../specification/40-example-reproducibility-and-materialization.md), and [Specification 50](../specification/50-materializer-closure-integrity.md)
- [#467/#494 L1 implementation-plan amendment](../planning/active/issue-467-494-l1-current-project-revision-implementation-plan-amendment-2026-09-27.md)
