# #349 Visual Capability Feedback Architecture Review

**Decision:** accept the follow-up correction.

## Reviewed flow

```text
Theme role binding -> Scene paint completion -> SceneBuildError -> RenderFailed -> CLI diagnostic
View icon binding -> completed Icon primitive -> profile validation -> RenderFailed -> CLI diagnostic
```

The reviewed implementation preserves a diagnostic code and pointer through
Theme and Scene, but the first flow is not adapted at the use-case boundary.
The second flow has no provenance for the author-owned binding. The resulting
fallback `/` pointer and code-as-message violate the Specification 63 promise
of an exact pointer for visual capability failures.

## Accepted correction

`SceneBuildError` remains the owner-neutral transport for a completed Scene
failure. It will expose its already stored stable code and pointer at the
render-use-case boundary, where it becomes `RenderFailed` with a canonical
diagnostic message. Scene completion retains the Theme role-property pointer;
it does not add Theme objects or diagnostic policy to adapters.

Completed icon primitives will carry the binding source pointer needed solely
for pre-adapter capability validation. This is placement provenance, analogous
to existing `source_ref`, not a reintroduction of View parsing into Scene or an
adapter. `validate_surface_visual_profile` will use that provenance for an
unsupported icon. It will report a capability-specific canonical message.

The correction will add a compact central message mapping for the closed
capability diagnostics. The mapping is presentation policy shared by Scene
transport and profile validation; it is not target syntax. Unknown diagnostic
codes retain their existing code-as-message fallback so this slice does not
alter unrelated error contracts.

## Target evidence decision

Required treatments are rejected during Scene completion before adapter
invocation. `decorative-optional` treatments are omitted there on baseline.
For admitted profiles, SVG is checked structurally and PNG is checked from
rendered pixels rather than an incidental byte substring. PDF remains a
baseline-only route; no direct rich-surface-to-PDF adapter characterization is
product evidence.

## Whole-architecture result

The correction keeps the ownership chain intact: Layout supplies bounds;
Theme supplies role binding; Scene completes/omits treatments and transports
their provenance; profile policy admits completed values; adapters serialize.
No generic profile, PDF rich route, renderer fallback, asset feature, or
compatibility alias is introduced. The exact v0.7 icon profile sets remain
unchanged.

