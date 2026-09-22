# Issue 99 Step 5 Renderer/Scheduler Protocol Design Review

**Decision:** Approved for implementation planning.

The protocols are intentionally behavioral and do not elevate a particular
scheduler implementation to architectural authority.  The renderer protocol
preserves the completed-Scene boundary, while Scheduler keeps scheduling facts
outside presentation.  The design does not reopen the removed staged module
decision from Issue 94 and introduces no compatibility or output-target policy.
