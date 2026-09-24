# Issue #364 — Whole-Architecture Review

The correction restores, rather than expands, the established authority chain.
The render use case owns the resolved closure and its asset root; callers do
not assemble production adapters. Font metrics and raster outlines now receive
the identical declared root, but remain consumed in their separate layers:
Layout uses metrics, while PNG/PDF adapters use bytes after Scene completion.

No fallback host font, adapter-side Context discovery, or Scene resource access
is introduced. The design is provider-neutral: package locators remain package
lookups and `context` locators work after either draft ingress or materialized
snapshot rewriting. It therefore addresses the defect structurally and avoids
a CLI-only or materializer-only condition.

Approved for implementation with the acceptance tests in the accompanying
design document.
