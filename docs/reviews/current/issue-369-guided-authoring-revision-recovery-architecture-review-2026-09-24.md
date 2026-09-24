# Issue 369 architecture review

## Result: accepted

The design keeps the two concurrency domains distinct: immutable Store commands
retain opaque revision tokens, while authoring-workspace commands declare the
workspace content identity as their local-file equivalent precondition. The
public revision read is a CLI adapter over the existing Core identity and does
not create a new persistence abstraction.

The result correction removes an ambiguous field rather than retaining a
misleading compatibility alias. The diagnostic includes both values at the
authoring boundary. `init` aligns the generated Store selector with the copied
Contexts, and materializer guidance preserves the explicit `--write` evidence
publication gate. No presentation, Layout, Scene, renderer, or scheduling
responsibility changes.

Implementation may proceed only with the published result contract, focused
cross-boundary tests, full-suite verification, and public materializer checks.
