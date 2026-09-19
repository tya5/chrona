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
| M9 | Design complete; implementation incomplete | Output coordinator has SVG capability evidence; WD-3 defines release packaging. | Implement package validation, then execute full release acceptance. |
| M10 | Design complete; implementation not started | FD-1 design/fixture/review. | Runtime and UC-16 evidence after current-profile release. |
| M11 | Design complete; implementation not started | FD-2 design/fixture/review. | Runtime and UC-17/18 evidence after M10. |
| M12 | Design complete; implementation not started | FD-3 design/fixture/review. | Runtime and UC-19–21 evidence after M11. |
| M13 | Design complete; implementation not started | Roadmap and successor design reviews. | Cross-profile release evidence after M10–M12. |

Implementation may start only at a `Design complete; implementation not started`
milestone or resume only after every listed open condition is closed and its owning
design review is updated. A blocked milestone cannot be bypassed by a later release.
