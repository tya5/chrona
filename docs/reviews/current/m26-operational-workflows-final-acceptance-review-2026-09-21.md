# M26 Operational Workflows Final Acceptance Review — 2026-09-21

**Decision:** Accepted and released.

## Scope verified

- UC-10 is exposed by `actual-intake` and `actual-resolve`, each consuming only a
  Command v0.2 with immutable Actual-set, batch, and Project references.
- UC-11 is exposed by `command-check` and `command-apply`; exact replays are durable,
  changed command-ID reuse rejects, and `propose-set` is not a reachable CLI verb.
- UC-12 is exposed by create-once `baseline-capture` and verified
  `baseline-compare`; independent configured stores are permitted only after each
  reference verifies.

## Evidence and outcome

The M26 acceptance manifest lists A26-01 through A26-10 and their automated evidence.
The full suite passes with `PYTHONPATH=src python -m pytest -q` (184 tests), and the
conformance runner passes. Result destinations are create-once, accepted/rejected work
maps to exit 0/2, and request/result publication failures map to exit 3. No operation
uses a working-tree default, branch, clock, title match, renderer fallback, or direct
source-file mutation.

## Boundary confirmation

M26 adds no scheduler, Project, View, Scene, or renderer authority. The local Actual
adapter writes only its declared CAS target and baseline capture writes only the named
append-only registry entry. This closes I26-7 and M26.
