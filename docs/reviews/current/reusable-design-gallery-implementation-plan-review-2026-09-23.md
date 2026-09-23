# Reusable Design Gallery Implementation Plan Review

**Date:** 2026-09-23  
**Scope:** I-GDF-1 through I-GDF-7 in the reusable gallery implementation plan
**Decision:** Accepted

## Review result

The implementation plan preserves the published architecture.  It makes
effective ordinary resources the sole shared input to rendering and Design
Space inspection, keeps package acquisition outside rendering, and postpones
corpus/gallery curation until a locked, materializable package path exists.

## Boundary findings

| Risk | Plan control | Result |
| --- | --- | --- |
| Summary becomes an alternate View/Theme model | pure projection of resolved resources; no closure input | accepted |
| Gallery config affects output | catalogue validation is documentary only | accepted |
| Mutable local path persists in guided render | v0.2 selector plus verified lock replaces guided v0.1 | accepted |
| Package resolver leaks into normalizer/Layout/Scene | acquire/locked resolver hands ordinary resources to existing normalizer | accepted |
| Stage-3 keeps package inheritance | ejection creates a complete explicit bundle and `derivedFrom` receipt | accepted |
| Attractive fixtures introduce SVG-only behavior | initial fixtures use current portable Scene vocabulary; #345 gates anything else | accepted |
| Generated-output work slows every slice | one final batched SVG review, except changed public evidence | accepted |

## Required implementation controls

1. Validate each new schema through the repository schema-inventory and
   annotation gates before adding runtime use.
2. Keep package content identity defined over canonical manifest/member bytes;
   no filesystem mtime, absolute cache root, or checkout path may contribute.
3. Treat any request for package nesting, remote lookup, a new resource kind,
   raw visual content, or renderer-specific capability as a design deviation.
4. Publish every completed slice serially and confirm its GitHub state before
   beginning its dependent slice.

No design amendment is required before I-GDF-1.
