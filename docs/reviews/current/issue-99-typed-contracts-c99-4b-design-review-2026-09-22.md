# Issue 99 C99-4B Optional Review Contract Design Review

**Decision:** Approved for implementation planning.

The review finds that the remaining opaque optional-resource path would defeat
the C99-4A closure boundary if retained: it lets later consumers distinguish
and reinterpret serialized documents by kind.  Exact schemas already exist
for the materialized optional review resources, including the externally
referenced revision-store schema required by snapshot refs.  The design keeps
schema authority singular and does not move policy into contracts.

The work is consistent with Issue 58 because contracts add no geometry; Layout
continues to own placement and Scene remains a completed-placement projection.
It is consistent with Issue 99 Steps 1–3 because the use case remains the sole
orchestrator, import direction remains inward, and registries remain unchanged.
No renderer or scheduler protocol is introduced; that is Step 5.
