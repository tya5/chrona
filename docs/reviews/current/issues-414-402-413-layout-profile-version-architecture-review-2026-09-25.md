# Architecture Review — Annotation Route Policy Versioning (#413)

**Decision:** Accepted.

The v0.7 migration is required.  `annotationRouting` changes the declarable
Layout Profile surface, so retaining the v0.6 identity while accepting the new
field would make closure and schema evidence dishonest.  Making the new limits
mandatory also prevents a hidden fallback to dependency routing.

| Boundary | Result |
| --- | --- |
| Contract truth | Pass. v0.7 identifies the exact grammar consumed by runtime and closure validation. |
| Compatibility | Pass. Removing v0.6 avoids two policy paths and preserves the project's explicit-migration rule. |
| Responsibility | Pass. Profile supplies bounded policy; Layout routes and completes geometry; Scene/adapters only project it. |
| Regression containment | Pass. Independent values and tests prevent annotation tuning from changing dependency routes. |

The implementation plan may proceed only as one atomic migration of public
resources and closure consumers; an isolated schema addition or a defaulting
reader is rejected.
