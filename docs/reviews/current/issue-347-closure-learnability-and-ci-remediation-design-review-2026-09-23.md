# Issue #347 Closure Learnability and CI Remediation Design Review

**Status:** Accepted  
**Date:** 2026-09-23

## Decisions

### Closure diagnostics

`ClosureError` gains an optional author-facing detail while retaining its stable
diagnostic ID and RFC 6901 source reference.  Every `SchemaContractError`
conversion carries its selected `SchemaViolation.message`; non-schema closure
errors retain their ID-only message.  The CLI remains the sole JSON diagnostic
serializer.  This repairs a lost value at the ingress boundary without leaking
validator types downstream.

### Schema annotation applicators

The lint already traverses `items`, `oneOf`, and `anyOf`; #347's broader claim
is stale.  Its `allOf` conditional handling currently suppresses nested
`if`/`then`/`else` nodes, however.  The lint will recurse into every supported
conditional child and require its own description/examples where authorable.
Pure `$ref` reuse remains exempt.  Existing schema annotations will be added
only where the strengthened live gate identifies an actual missing node.

### CI

Keep the Ubuntu/macOS matrix and full test gate for pull requests and `main`.
Restrict `push` to `main`, removing same-repository branch/PR duplication; use
the default shallow checkout; and enable pip caching keyed by the dependency
metadata.  Retain workflow concurrency cancellation.

A session-scoped public-render cache is rejected: under xdist it is
worker-local and does not remove cross-worker rendering; a shared filesystem
cache would introduce synchronization, lifecycle, and fixture-mutation
authority into tests.  Tests continue to own temporary outputs.

### Issue record

Add a concise #322 closure comment linking its proposal to the accepted
Specification 58 alternative.  This is a historical decision record, not a
reopened implementation.

## Architecture review

All changes are ingress/quality/CI concerns.  They do not alter Project,
Actual, View, Layout, Scene, renderer, materializer, or immutable Context
authority.  The diagnostic detail crosses only the existing error boundary;
the linter remains tooling-only; and CI optimization cannot weaken required
platform verification.
