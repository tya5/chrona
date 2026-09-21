# M26 Operational Workflows Design Review — 2026-09-21

**Decision:** Approved for implementation planning.  
**Scope:** UC-10 external Actual intake/reconciliation, UC-11 revision-bound
automation, and UC-12 named baseline capture/compare.

## Boundary audit

| Boundary | Decision | Review result |
|---|---|---|
| Project ↔ Actual | intake/reconcile target only an Actual-set; Project IDs are verified read-only inputs | pass: no schedule or planned-data mutation |
| Actual ↔ external source | normalized batch preserves system/key/content identity; adapter does not fetch locator | pass: retry and provenance have an owner |
| Command ↔ Store | v0.2 target is complete immutable reference and CAS precondition repeats its revision/digest | pass: no raw path or implicit tip remains |
| Command ↔ CLI/CI | check and apply share one request/result contract; only apply may write through Store | pass: console and checkout are non-authoritative |
| Project ↔ baseline | capture records the verified Project reference in create-once registry resource | pass: no copied schedule/Scene or retargeting |
| baseline ↔ comparison | compare verifies stored baseline Project and explicit candidate separately | pass: cross-store inputs stay pinned |
| result ↔ artifacts | atomic result records input closure and declared output references | pass: collisions and interruption have deterministic behavior |

## Design corrections completed during review

The v0.2 schema initially specified only the new intake, resolution, and capture
payloads. Before approval it was extended to close the legacy operational payloads
(`editActualObservation`, `unresolveActualObservation`, and `setTypedField`) rather
than leaving an implementation-time decision. YAML date examples were also changed to
quoted strings so generic YAML/JSON schema validation does not reinterpret them as
native date values.

**Amendment, 2026-09-21:** I26-3 identified that Actual-set v0.1 cannot retain the
source content identity required by the intake replay rule. The operational profile now
requires Actual-set v0.2, whose externally identified observations retain that identity.
This amendment is approved before I26-3 starts; v0.1 remains legacy-readable and is not
silently upgraded.

**Amendment, 2026-09-21:** resolved v0.2 observations retain their external identity
and source content identity. Reconciliation changes only alignment/Project object ID;
otherwise deduplication would be lost after an operator resolved a record.

**Amendment, 2026-09-21:** I26-6 requires a concrete Store-config format. The initial
profile is local-only, identity-exact, and credential-free (`store-config/v0.1`). This
closes CLI Store selection without introducing a default root or provider fallback.

**Amendment, 2026-09-21:** I26-6 also requires a concrete local Actual Store write
layout. ADR-0027 defines immutable token directories plus an adapter-private CAS tip;
this closes command-apply without admitting a mutable path as an input.

**Amendment, 2026-09-21:** a missing local Actual CAS pointer is not implicitly
bootstrapped by an M26 command. Provisioning is an adapter-administration action over a
verified immutable reference; command execution rejects missing pointers.

## Evidence checked

- `35-operational-review-workflows.md`, ADR-0024 through ADR-0026, all four successor
  schemas, and accepted/rejected examples agree on immutable closure and no title
  matching.
- Direct JSON Schema validation passes for the published examples.
- Existing conformance runner and `git diff --check` pass without changing product
  behavior.

## Residual implementation risks and prescribed controls

| Risk | Required control |
|---|---|
| filesystem adapter accidentally accepts a mutable file | adapter tests require exact reference verification and reject absent revision/digest |
| replay ledger becomes non-durable | make its Store-owned persistence and command-ID collision tests part of the command-engine slice |
| partial result file survives a crash | use create-new temporary output plus single rename and collision tests |
| baseline registry overwrites a name | implement create-if-absent, never update, and test concurrent/collision outcome |
| parser scope creeps into core | accept normalized batch bytes only; connector work needs a later ADR |

No unresolved product choice remains. The next permitted activity is the published
implementation plan; any failure of a listed invariant returns work to this design
review before implementation proceeds.
