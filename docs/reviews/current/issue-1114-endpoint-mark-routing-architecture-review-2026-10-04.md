# Issue #1114: architecture review

Reviewed design: [endpoint-mark routing](../../design/issue-1114-endpoint-mark-routing-design-2026-10-04.md).

| Authority / adjacent design | Consistency decision |
| --- | --- |
| Spec 09; Spec 33 surface phase ownership | Layout chooses and validates geometry; Scene only observes, adapters serialize. No semantic registry, Theme or mark-size change. |
| Spec 33 comparison-host egress | Named comparison marks may still cover a temporal anchor during its terminal corridor; primary marks are not blanket-exempt. |
| Spec 50 entry policies; #1084/#1072 | Keep safe candidate order and side-entry/back-route bounds; reject body traversal at all entry modes. Correct the broad endpoint exemption and unsafe fallback promise. |
| #1059 route self-overlap | Existing invariant/repair remains; repaired paths additionally pass mark safety. |
| #1046 rounded routes; #1044 centred terminals | Validate actual rounded geometry against primary marks; trimming preserves safety. Do not change terminal tokens or geometry module while dev B owns #1105. |
| Lane suppression evidence and required labels | Preserve label safety and typed attempt evidence; safety overrides visible overflow in both row modes. |

Decision: design is consistent after the Spec 50 correction. No public schema,
Project interpretation, View syntax or resource identity changes. Implementation
acceptance remains unverified. Risks to measure: suppressed fallback count,
comparison corridor interactions, rounded-path clearance and byte changes of
previously compliant routes. Any broader candidate reordering requires revisiting
design, not opportunistic inclusion of the mixed WIP.
