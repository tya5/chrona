# FD-3 Collaboration, Hosted Synchronization, and Audit Design Review

**Date:** 2026-09-19  
**Disposition:** Accepted for the future-capability implementation gate

## Evidence reviewed

- `20-collaboration-successor.md` owns hosted synchronization, merge, policy,
  approval, and audit boundaries.
- `ADR-0016-explicit-collaboration-merge-and-audit.md` fixes explicit merge and
  provenance as the compatibility decision.
- `collaboration-command-v0.2.schema.yaml` and `collaboration-v0.2.yaml` cover
  stale writes, conflict objects, approval mismatch, denial, and behind replicas.
- Store, Application Architecture, Command, Quality, and Federation specifications
  preserve their existing semantic ownership.

## Result

The design rejects last-writer-wins and never treats a hosted tip, presence signal, or
renderer state as Project authority. Conflicts remain typed, durable, and Command-
resolved; authorization/approval records constrain persistence without changing the
semantic model. Federation remains parent-side and pinned. No unresolved migration or
cross-owner ambiguity was found.
