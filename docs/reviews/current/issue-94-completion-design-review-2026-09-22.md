# Issue 94 Completion — Architecture Design Review

**Reviewed baseline:** `233593b6470ced337dd9f9d30203a7bf26f8b4ce`

## Review result

The Issue 94 completion plan is approved for implementation in its declared
order.  It reduces rather than expands the executable architecture.

| Boundary | Review finding | Disposition |
| --- | --- | --- |
| Product reachability | The 19 staged modules are test-only.  Wiring them to the CLI would create undocumented commands and false delivery claims. | Delete modules and dedicated tests; preserve use-case text as design intent. |
| Resource ingress | Shared `chrona/presentation` version labels conflate distinct resource kinds. | Rename identities atomically and reject legacy labels. |
| Normalization → Layout | Defaulted `SurfaceContentInput` permits incomplete input to cross the authoring boundary. | Require a completed input at construction. |
| Layout → Scene → renderer | The current surface implementation and Specification 50 already enforce the intended geometry ownership. | Make the seam normative in Specification 08; do not add a second handoff type. |

## Consistency with the overall architecture

The plan retains the dependency direction in Specification 09: canonical inputs
are normalized before Layout; Layout owns measurement, allocation, and routing;
Scene creates primitives; SVG/PNG adapters serialize only completed primitives.
Deleting inactive collaboration, command, extension, release, and successor
scheduling sketches does not alter the current CLI evaluation pipeline.

The use-case catalog explicitly distinguishes library/design evidence from the
current user product surface.  Therefore deletion is honest: a future UC needs
a new approved product route and boundary test rather than dormant source code.
The kind-specific resource identities make closure diagnostics accurately name
the contract being validated, without legacy acceptance in Layout, Scene, or
the materializer.

## Non-goals and risks

No retained compatibility is promised for old resource labels or direct
construction of incomplete internal values.  The risk of a broad rename is
contained by one atomic resource-identity PR and the five public materializer
contexts.  The risk of an accidental deletion is contained by the zero-staged
reachability lint, full test suite, and no-output-diff requirement.

## Authorization

P94-3 through P94-6 may proceed only in the order declared by the design plan.
Each merged slice is the basis for the next slice.
