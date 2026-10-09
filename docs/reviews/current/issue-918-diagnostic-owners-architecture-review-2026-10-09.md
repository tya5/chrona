# Issue 918 — architecture review

Reviewed public base: `546f7c3f9e700afa7553632d8dd6ac0c94a348a0`.
Design: [owner and transport contract](../../design/issue-918-diagnostic-owners-design-2026-10-09.md).

| Boundary / authority | Finding |
| --- | --- |
| Project/View identity (05/06) | Pointers refer to explicitly bound Project objects; View, entity, calendar and relation sources are not guessed to be objects. No source resource syntax changes. |
| Layout → Scene → adapters (08/50, ADR-0031) | Provenance is a non-rendered sidecar. Layout retains all geometry ownership; Scene only projects completed provenance/primitives; adapters receive no new placement policy. Serialized diagnostic identities and image bytes must not change. |
| Operational results (35) | Tuple strings use the existing leading-code parser. CAS/replay/write behavior and automation-result schema remain unchanged; owner detail enriches existing messages. |
| Schema diagnostics (56) | Keep deterministic pointers and expected/type descriptions; do not echo sensitive raw payloads to satisfy a value assertion. |
| Agent result (66) | CLI's sole success machine channel becomes stdout; MCP retains its existing structured-row shape. Shared ledger facts and cause-based collapse preserve multiplicity/first occurrence. |
| Earlier diagnostic design (782/829) | Completes deferred channel/provenance decisions, not a duplicate error catalogue. Inventory and operand assertions prove different obligations. |

Decision: proceed with this contract after normative updates and implementation
plan publication. Review implementation against each literal A1–A12 row; this
review is not release acceptance. Remaining risks are coverage across 488
sites, missing producer provenance on suppressed placements, accidental warning
identity changes, whole-string consumers, and CLI scripts reading stderr.
Synthetic fixtures, explicit source capture, mutation checks and byte/row audits
are the required controls. Coordinate shared Layout files with dev B; do not
use corpus tuning to absorb a change.

Follow-up review (6085291520), source baseline `48465773`: Theme schema uses
`body.colorScales`; correcting the illustrative pointer requires no syntax
change (Spec 56). View normalization owns annotation array provenance (06),
while Layout still owns target eligibility and geometry (08/50); provenance
must not enter identity or Scene serialization. Model-owned scale errors are
translated once at the application boundary (66), not guessed by adapters.
Standalone materialization serializes the existing failure report only at its
adapter boundary (40); library exceptions and success bytes remain intact.
Decision: accept this correction for implementation-plan publication. A13–A15
remain unaccepted until source/transport tests and the exact-main gate prove
them; identity leakage, late scale-value failures and lost diagnostic rows are
the additional review risks.
