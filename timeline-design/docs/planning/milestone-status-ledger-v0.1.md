# Milestone Status Ledger v0.1

**Status:** Authoritative delivery-status ledger for design recompletion

This ledger owns status only. The roadmap owns ordering; specifications own semantics;
reviews and test/fixture references are evidence. `Complete` means its documented exit
evidence is present, not that a later product release is complete.

| Milestone | Status | Entry / exit evidence | Open condition |
|---|---|---|---|
| M0 | Complete | Core conformance and scheduler tests; `core-v0.1-stable-readiness-review.md`. | None for current scope. |
| M0.5 | Complete | Delivery-profile vocabulary/state/evidence fixtures. | M1 supplies its reproducible resolution dependency. |
| M1 | Complete | Revision Store conformance and resolved package closure. | None. |
| M2 | Complete | Presentation conformance, deterministic Scene/SVG evidence. | Only SVG is claimed. |
| M3 | Complete | Revision-bound Command/CAS/undo evidence. | None. |
| M4 | Complete | Federation conformance and M4 reuse review. | None. |
| M5 | Complete | CLI/review plus AI proposal adapter; fingerprint-bound policy decision and Command/CAS acceptance tests. | None. |
| M5.5 | Complete | External Actual identity/intake review and tests. | None. |
| M6 | Complete | Interactive review and accessibility/SceneDelta evidence. | None. |
| M7 | Complete | Gesture, annotation, Actual reconciliation, Snapshot, conflict/undo evidence. | None. |
| M8 | Complete | Trusted declarative package closure/lifecycle review and tests. | None. |
| M9 | Complete | Declared SVG output coordinator, capability/fidelity evidence, AI-inclusive UC-01–15 acceptance manifest, and exact release-package validation. | None; publication remains a runtime operation over a named closure. |
| M10 | Complete | DateTime/DST value, v0.2 Project Format, endpoint and recurrence runtime, opt-in migration, UC-16 acceptance and M10 final reuse/release review. | None. |
| M11 | Complete | Date-only capacity validation, deterministic explicit leveling proposal/CAS acceptance, isolated cost observations, UC-17/18 acceptance and reuse review. | None. |
| M12 | Complete | Explicit conflict/CAS resolution with two-parent provenance, append-only audit observations, and labelled replica status; UC-19–21 evidence reviewed. | None. |
| M13 | Complete | Fixed successor v0.2 closure, exact UC-16–21 evidence validation, and blocked/published release boundary. | None. |
| M14 | Complete | User-selected View grouping plus profile-selected headers/separators/bands/gaps in deterministic Review SVG. | None. |
| M15 | Complete | Generic table-timeline SVG adapter, Controller Z user-editable preset, M15 final review, conformance, and 87 tests. | None. |
| M16 | Complete | Generic read-only summary adapter, Controller Z user-editable profile/preset, M16 final review, conformance, and 88 tests. | None. |
| M17 | Complete | Generic Theme role resolution, light/dark user-editable presets, M17 final review, conformance, and 88 tests. | None. |
| M18 | Complete | M15–M17 cross-profile/reuse release review; full conformance and 88-test evidence. | None. |
| M19 | Complete | Layout Profile runtime validation, deterministic Layout Manifest, old-profile rejection, M19 final review, conformance, and 89 tests. | None. |
| M20 | Complete | Constraint solver and slot-based review rendering, M20 final review, conformance, and 90 tests. | None. |
| M21 | Complete | Generic calendar/table/relation/annotation primitives, M21 final review, conformance, and 91 tests. | None. |
| M22 | Complete | Common human/AI declarative preset validation, M22 release review, conformance, and 92 tests. | None. |

Implementation may start only at a `Design complete; implementation not started`
milestone or resume only after every listed open condition is closed and its owning
design review is updated. A blocked milestone cannot be bypassed by a later release.
