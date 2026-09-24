# Issue 365: implementation plan

## Acceptance

- Draft `1600xauto` resolves a finite block extent and renders 50/100-row
  table-timeline inputs without guessing.
- Immutable Contexts reject no new syntax and retain fixed viewport behavior.
- Numeric row overflow reports requirement, availability, row count, row
  minimum, and a deterministic explicit viewport hint.
- `compactness` is absent from View schema, typed fixtures, examples, and
  specification.
- The 30/100 row curriculum is public and covered by focused tests.

## Slices

1. **D365-1 — diagnostic fidelity.** Preserve Layout diagnostic detail through
   Scene and render errors; add numeric table/timeline overflow facts and
   focused direct/CLI tests.
2. **D365-2 — typed Draft auto extent.** Add the Draft-only request, CLI
   grammar, and Layout content-extent resolver.  Resolve before final layout;
   test fixed, auto, unsupported surface, SVG, PNG, and guided Draft paths.
3. **D365-3 — contract correction.** Remove `compactness` from schema,
   examples, fixtures, typed View use, and normative documentation; prove an
   old field is rejected.
4. **D365-4 — public scale curriculum and release gate.** Add 30/100-row
   fixtures and focused evidence tests, run full pytest and public materializer
   checks, inspect generated SVG differences, review architecture/acceptance,
   then publish and verify CI.

Each slice is independently testable, but implementation is published as one
coherent Issue 365 change because auto extent, diagnostic guidance, and scale
evidence form one user-visible fit policy.
