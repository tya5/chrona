# Architecture Review — Committed Capability Slides (#434)

**Decision:** approved for implementation. **Reviewed:** [#434 design](../../design/issue-434-committed-capability-slides-design-2026-09-27.md).

- **No semantics change.** The capabilities already exist and are specified (#388, #389, #403, #404, #406, #410, #413); this adds public evidence and derived reports.
- **Evidence isolation.** A new slide with its own resources, plus one paint-only change on `controller-z/annotations`. Every other slide changes only in provenance where it shares Controller Z `executive-light`.
- **Tools.** Both reports are derived. The unreferenced-file reason list is explicit data in the tool, not a silent allow-list.
- **Coordination.** The in-flight #426, #466 and #467 View version bumps will migrate the new View's `version` line with the rest.
