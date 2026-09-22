# Issue 99 Step 5 — Renderer/Scheduler Protocol Implementation Plan

**Status:** Approved implementation plan.  **Design authority:**
`issue-99-renderer-scheduler-protocol-design-2026-09-22.md`, merged by PR
#140.

## Scope

Introduce narrow protocol-owned scheduling/rendering outcomes and inject them
into the review render use case, retaining the reference scheduler and v0.5 SVG
serializer as default adapters.

## Steps

1. Add immutable `ScheduleOutcome`, `Scheduler`, and `Renderer` ports in
   `core.ports`; keep them free of concrete scheduling/presentation imports.
2. Add small adapters beside their concrete implementations: the scheduler
   adapter maps `ScheduleResult` to `ScheduleOutcome`; the renderer adapter
   delegates to the existing completed-Scene serializer.
3. Extend `RenderRequest` with default protocol dependencies.  Replace direct
   concrete imports/calls in the use case; preserve `RenderRejected`,
   `RenderFailed`, diagnostics, and output bytes.
4. Add fake-port tests and structural import checks.  Verify both snapshot and
   primary scheduling use the injected Scheduler.
5. Run focused tests, full pytest, conformance, import/reachability checks,
   all materializers, and generated-SVG diff.  No artifact changes.

## Acceptance criteria

- The review use case imports only ports for scheduler/renderer behavior.
- A fake Scheduler and Renderer execute the use case without concrete adapter
  calls.
- Defaults reproduce all current SVGs and stable diagnostics.
- No new scheduler algorithm, SVG output format, or CLI selection policy.

## Publication boundary

One implementation PR follows this plan. Step 6 documentation begins only
after it merges.
