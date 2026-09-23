# #348 Reusable Gallery Design Correction Review

**Date:** 2026-09-23  
**Trigger:** independent tree review in [#348](https://github.com/tya5/chrona/issues/348)  
**Decision:** Accepted — pause package rollout; establish corpus evidence first

## Findings accepted

The review correctly found that ordinary presentation resources can be paired,
Context-pinned, and materialized before package acquisition exists; delaying
the first gallery design for package machinery was not justified. It also found
three unaccounted facts: dead `controller-z/variants` rendering evidence, no
committed preset example, and no package-aware materializer/store plan. The
package specification additionally lacked required user command forms and
stable diagnostics. The existing semantic `profile-v0.2` package is not a
generic envelope, but its adjacent lifecycle/identity model must be explicitly
considered rather than ignored.

## Corrected architecture

The immediate gallery path is ordinary corpus resources and immutable Contexts.
The materializer remains the sole public SVG producer. The catalogue validates
declared provenance and pair identity; it never resolves a package. Package
acquisition is deferred until actual reusable content and a consumer establish
the need, at which point a new architecture review must decide its relationship
to the profile package and the materializer store boundary.

The provisional Summary and package/lock implementations are removed in the
correction rollout rather than preserved as an unsupported public path. This is
a clean replacement, not a compatibility layer.
