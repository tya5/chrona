# C-GDF-2 Paired Ordinary Corpus Gallery Design Review

**Decision:** Accepted

The materializer already selects a slide-specific Context from a declared
corpus manifest. Controller Z's Executive and Plan-only slides can therefore
remain ordinary independent closures. Pair validation will compare only
Context reference identity: Project and Actual references must be equal, and
at least one of View/Theme/Color Scheme/Layout must differ. This proves the
claimed semantic control without inferring it from titles or rendered bytes.

The successor catalogue is a documentation validator. It reads manifest and
Context YAML through injected corpus paths, validates finite provenance and
target claims, and never imports closure resolution, rendering, scheduling, or
package code. Gallery prose cannot influence a materializer invocation.

No new Scene capability, package resolver, compatibility reader, or resource
kind is required. The design is consistent with Specifications 32, 55, and 58.
