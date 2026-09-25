# Architecture Review — Project-Format Package Requirement (#405, #406, #407, #408, #400)

**Result:** Accepted.

The profile package declares a closed dependency on the Project source format.
Updating the Project without updating that declaration would falsify immutable
closure provenance. Versioning the package preserves the dependency boundary:
resource resolution validates it before Projection/Layout, and no renderer or
adapter learns a source-format fallback.
