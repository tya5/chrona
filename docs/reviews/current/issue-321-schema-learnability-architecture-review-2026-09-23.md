# Issue 321 Schema Learnability Architecture Review

**Review scope:** [56 Schema Authoring and Diagnostics](../../specification/56-schema-authoring-and-diagnostics.md),
the live schema inventory, Core validation, presentation contract ingress, and
the normal rendering pipeline.
**Result:** Accepted as the basis for implementation planning.  No schema or
runtime behavior changes in this review.

## Boundary findings

| Boundary | Finding | Decision |
| --- | --- | --- |
| Schema annotation | Descriptions and examples are JSON Schema annotation keywords, but an ungoverned convention would drift. | Keep annotations in the owning schemas and enforce them with an inventory-driven lint; do not add a parallel documentation model. |
| Contract versus Core validation | Presentation contracts retain pointers while Core emits raw validator messages. | Share a structural-explanation helper below both boundaries, then map to their existing public error records.  Semantic validation remains separate. |
| Resource identity | A pointer alone cannot identify which acquired resource failed. | Contract errors retain their existing identity/kind context; Core diagnostics retain their Project input boundary.  The pointer is never overloaded as identity. |
| Union diagnostics | Generic `oneOf` contexts can report unrelated alternatives. | Use real discriminator values where available; otherwise summarize legal key-shapes.  Never introduce fake selector fields just for diagnostics. |
| Project schedule | `fixed` duplicates two author-visible forms and propagates ambiguity through validation. | Move to `fixed-point` and `fixed-span` in one v0.6 migration.  Scheduler internals may share placement code, but source syntax has no alias. |
| Documentation drift | A manually maintained registry of contract IDs would itself drift. | Derive current identifiers from live inventory/schema `$id`; classify normative examples current or historical at their occurrence. |
| Downstream rendering | Richer ingress messages could tempt View/Layout/Scene to inspect raw schema data. | The helper returns only rejected ingress information.  A successful parse still produces the same frozen typed contracts; no downstream module imports it. |

## Architecture conformance

The proposal maintains the existing direction:

```text
bytes -> YAML -> schema explanation -> immutable contract / Core input
                                      -> scheduling -> View -> Layout -> Scene -> renderer
```

Descriptions, examples, and documentation checks are build-time/reference
surfaces.  `SchemaViolation` is an ingress failure value and never enters a
successful closure.  Consequently the work neither changes scheduling
authority nor permits a renderer to supply a fallback for malformed authoring
input.  The #255 pointer behavior remains the instance-location basis for the
new explanation contract rather than being replaced by a schema-location or
line-number approximation.

The v0.6 schedule change is structurally cleaner than an `at`/`start` shape
heuristic.  It preserves semantic placement because both fixed tags lower to
the existing fixed-placement authority, while forcing every authorable source
and profile declaration to name its intended form.  Rejecting v0.5 after the
atomic first-party migration is intentional: accepting both would retain the
same ambiguous public union and make annotation/diagnostic evidence misleading.

## Risk review

1. **Annotation bulk edits can encode wrong policy.** Each family must be
   reviewed against its existing owner; lint proves completeness, not semantic
   correctness.
2. **Validator context ordering can vary.** The shared helper must rank errors
   from explicit instance/schema information and tests must assert one result,
   rather than relying on iterator order.
3. **A migration can leave stale format claims.** The schema inventory, profile
   requirements, examples, CLI fixtures, docs gate, and installed resources are
   one acceptance unit.  A passing scheduler unit test is insufficient.
4. **Helpful prose can expose raw values.** Diagnostics name schema-controlled
   expected forms and value categories only; they do not echo arbitrary source
   strings or host file paths.

## Required implementation gates

1. Publish a concrete implementation plan naming the shared helper API,
   annotation-lint traversal, docs marker syntax, and every Project v0.5
   first-party migration target.
2. Land structural diagnostic tests before changing messages, including tagged,
   key-shape, required, enum, and unknown-property cases.
3. Land schema annotations in reviewable family batches under the lint, then
   migrate Project v0.6 in one atomic resource/consumer change.
4. Validate normative documentation references, public CLI diagnostics,
   full tests, materializers, generated SVGs, and installed-wheel behavior.

The design is complete.  Implementation may proceed only through those slices;
an isolated wording change or compatibility parser would violate the reviewed
boundary.
