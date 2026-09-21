# Issue 38 Example Reproducibility Design Plan

**Issue:** #38
**Status:** Active

## Goal

Restore reproducible public examples by aligning Context-version acceptance, immutable content identities, materialization, acceptance tests, and status evidence.

## Design sequence

1. Audit the public materializer, Render Context resolver, example manifests/contexts, acceptance tests, and CI workflow.
2. Define one current Context-version policy and explicit compatibility scope.
3. Define the authoritative generation path for Context references and expected SVG artifacts; preserve immutable identity verification.
4. Define test/CI responsibilities so every declared example is materialized and identity-checked.
5. Restore missing status/review documents only from verified historical content; never regenerate or invent prior evidence.
6. Publish an integrated boundary review and completed design.

## Non-goals

- no legacy Settings or deleted Theme contracts;
- no latest-resource fallback, mutable Context reference, or hand-waved hash mismatch; and
- no renderer-only exception for examples.
