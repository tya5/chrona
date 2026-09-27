# Architecture Review — Presentation Error Pointer Transport (#477)

**Design:** [selected design](../../design/issue-477-presentation-error-pointer-design-2026-09-26.md).

## Whole-architecture consistency

| Authority | Check | Result |
| --- | --- | --- |
| Specification 09, runtime coordinator | Stages report stable diagnostics while the coordinator transports them; it does not infer resource facts. | Consistent: detectors keep code, path and detail. |
| Specification 13, presentation boundary | Resource identity and failure ownership stay with the existing evaluation path. | Consistent: no closure or schema change. |
| Specification 30, Layout/Scene ownership | Geometry, measurement and paint detection remain in their owning layers. | Consistent: use case only converts exceptions. |
| Specification 56 and #450 | Schema ingress retains aggregate pointers and its existing dedicated transport. | Consistent: `PresentationIngressRejected` is not intercepted. |
| #371 actionability | The source pointer is detector-owned information, not CLI-generated advice. | Consistent. |
| CLI and adapter boundary | CLI serializes `RenderFailed.source_ref`; SVG/PNG/typeset adapters see only successful completed values. | Consistent. |

## Decision and risks

Approved without a living-specification or ADR change: this restores transport
of an already-carried pointer rather than introducing new semantics. The
principal risk is catching too broadly and changing unrelated error behavior;
the implementation must catch exactly the three known typed classes and retain
the existing `SceneBuildError`, ingress, font and closure paths. Tests must
exercise both actual CLI failures, not only synthetic exceptions. No unresolved
design question blocks implementation planning.

**Next:** [implementation plan](../../planning/active/issue-477-presentation-error-pointer-implementation-plan-2026-09-26.md).
