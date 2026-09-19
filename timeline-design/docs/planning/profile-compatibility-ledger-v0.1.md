# Current and Successor Profile Compatibility Ledger v0.1

**Status:** Authoritative compatibility inventory for design recompletion

| FD | Versioned capability | Opt-in trigger | v0.1 invariant | Migration / rejection rule | Delivery owner |
|---|---|---|---|---|---|
| FD-1 | DateTime/DST, `timeline/v0.2` | Explicit v0.2 Project/profile and zone policy | A v0.1 Date remains timezone-free; Date-only scheduling is unchanged. | Mixed domains reject; v0.2→v0.1 downgrade rejects DateTime/recurrence values. | M10 |
| FD-2 | Capacity/accounting, successor resource-capacity inputs | Explicit capacity-set/evaluation request | Capacity, cost, and Actual observations do not alter v0.1 schedule authority. | Missing/incompatible units or stale proposal diagnose; only accepted current-revision Command changes a Project. | M11 |
| FD-3 | Collaboration/sync/approval, v0.2 collaboration commands | Explicit collaboration session and policy | A v0.1 Revision Store remains single-writer/CAS; no hidden last-writer-wins. | Divergence, policy denial, expired approval, or behind replica rejects/presents conflict without mutation. | M12 |
| FD-4 | Declarative extension lifecycle, package reference v0.2 | Pinned trusted package reference | Existing Core profile and temporal semantics remain authoritative; no executable package behavior. | Missing/untrusted/incompatible/cyclic/executable package rejects; no latest/fallback selection. | M8 |
| FD-5 | Output/release, output capability and release package v0.2 | Declared target capability profile and immutable release closure | Project/Scene semantics do not move into an output target; SVG success does not imply other targets. | Missing required capability rejects; excluded UC makes release package blocked and artifact-free. | M9 |

No row upgrades another row implicitly. A current-profile implementation may consume only
the versions named in its own release closure; successor inputs are ignored only by
explicit version rejection, never by lossy coercion or fallback. M13 may combine rows
only after each owner has passed its dedicated acceptance review and cross-profile
fixtures prove the listed invariants together.
