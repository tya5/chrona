# M12 Collaboration Implementation Readiness Plan

**Status:** Reopened — M12 correction authorized.

1. Implement typed stale/conflict objects and explicit resolution CAS.
2. Implement fingerprint-bound policy, approval expiry, and append-only audit.
3. Implement labelled replica/offline submission without remote-tip authority.
4. Run UC-19–21 acceptance and reuse/release review.

## Correction gate

The result-only prototype did not append audit observations or materialize an explicit
conflict resolution revision with both parent revisions.  The correction stores audit
records independently from Project state for every accepted or rejected submission;
an explicit `resolveMergeConflict` must use CAS and record the conflict's two parents
as provenance.  These records remain non-authoritative scheduling inputs.
