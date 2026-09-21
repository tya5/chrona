# Remaining Work Portfolio Plan

**Status:** Active
**Date:** 2026-09-21

## Ordering rationale

Issue 44 changes the identity/integrity contract used by Issue 38. It must be designed and decided before #38 is finalized. Issue 40 is an independent layout-correctness defect. Issue 41 repairs the current explicit-row/callout feature. Issue 42 extends vocabulary and therefore follows #41's corrected foundation.

## Phases

1. **#44 Integrity policy** — design plan, whole-system design/review, implementation plan, then implementation. Decide optional/required identity policy without weakening extension/package or command/baseline integrity.
2. **#38 Reproducibility completion** — reconcile implementation with the decided #44 policy; obtain the delegated pytest results; regenerate only CLI-derived expected artifacts; run materialization acceptance and close.
3. **#40 Typography-aware measurement** — design title/role measurement and required overflow diagnostics, then implement and verify.
4. **#41 Explicit-row and callout usability** — design and implement member labels, theme-sized symbols, same-row relation ports, baseline role, and annotation rail.
5. **#42 Slide-grade vocabulary** — design the shared/stacked overlay model, group headers, calendar/as-of policy, legend swatches, callout rail reuse, and mark labels; then implement in dependency order.

## Controls

Every phase follows: design plan → completed cross-boundary design/review → implementation plan → implementation/review. Each phase is published serially through GitHub. Existing immutable references, Scene ownership, and deleted legacy contracts remain constraints.
