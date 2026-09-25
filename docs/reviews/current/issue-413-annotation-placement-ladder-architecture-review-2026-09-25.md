# Architecture Review — Purpose-Independent Annotation Placement (#413)

**Decision:** Accepted.

The correction restores the intended authority chain.  Annotation purpose is a
semantic presentation decision, whereas candidate placement and suppression
are geometric failure policy.  Coupling the latter to two purposes made the
public finite-purpose contract non-materializable.

| Boundary | Result |
| --- | --- |
| View | retains the one finite fallback declaration and does not receive coordinates. |
| Normalizer | closes ladder and purpose independently into typed intent. |
| Layout | owns measured candidate selection, suppression record, route quality, and terminal geometry. |
| Scene/adapters | receive selected placements and semantic IDs verbatim; no fallback or route inference. |

The correction is compatible with the approved semantic distinction design and
does not add schema syntax or a renderer-specific primitive.  I413-2 may resume
only after this correction is public.
