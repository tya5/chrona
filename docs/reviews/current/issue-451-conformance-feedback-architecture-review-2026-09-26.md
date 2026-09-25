# Architecture Review — Conformance Feedback and Independent CI Execution (#451)

**Design under review:**
`issue-451-conformance-feedback-design-2026-09-26.md`.
**Decision:** Accepted for implementation planning.

## Boundary review

| Concern | Result | Required guardrail |
| --- | --- | --- |
| Tool authority | Pass | The runner captures process outcomes but does not parse/replace product or tool validation rules. |
| Derived output | Pass | Shared stale reporting compares supplied bytes without writing, and each producer retains its generator/validator ownership. |
| CI topology | Pass | `continue-on-error` is local to reporting steps; one final aggregator remains the sole job failure authority. |
| Dependency safety | Pass | Wheel/install/smoke cannot run after failed gate/test prerequisites; skip reasons are explicit. |
| Cross-platform behavior | Pass | Workflow control/result aggregation is Python, not bash; Windows gets the same independent reports. |
| #452 throughput | Pass | One logical invocation per check and one environment setup reduce redundant work without cached cross-run correctness state. |
| Security/operability | Pass | Output is bounded and command data is structured; no environment dump or arbitrary shell interpolation is introduced. |

## Required implementation controls

1. Declare check IDs and dependencies as static code data; do not make CI run
   arbitrary YAML/shell commands from a user-controlled source.
2. Capture process output in the runner and re-emit it under the check header,
   preserving a failing tool's existing actionable report.  Do not hide output
   behind the summary table.
3. Test the runner through injectable process invocation/clock seams rather
   than a product import or real failing repository mutation.
4. Keep the final workflow outcome helper minimal and test its accepted
   outcome vocabulary (`success`, `failure`, `cancelled`, `skipped`).  A
   cancelled workflow remains a cancellation, not a fabricated failure report.
5. Migrate stale tools atomically only after their common helper has exact
   byte comparison and newline behavior covered.  A partial migration must
   retain the original tool result until its report is verified.

## Conclusion

The design improves feedback, cross-platform evidence, and throughput without
moving product responsibility into CI.  It is coherent with #452 and #454's
separation of independent diagnostics from dependent actions.  A published
implementation plan is required before source/workflow changes.
