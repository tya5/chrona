# Issue #554 — Whole-architecture design review

**Decision:** approve [the design](../../design/issue-554-lane-followups-design-2026-09-29.md) against the published [plan](../../planning/active/issue-554-lane-followups-work-record-2026-09-29.md); implementation has not started.

| Boundary | Consistency finding |
| --- | --- |
| Project and Review identity (Specs 06/38, #467) | Generated lane IDs and explicit keys remain identity only. Display titles derive from selected Project titles; membership, count, and order do not change. |
| View and Theme (Specs 08/50, #501/#504) | View retains table/count intent. The singleton 03 resource explicitly removes its constant count column. Theme owns one closed-day paint shared by chart and key. |
| Layout (Specs 33/50, #466/#504) | Measured association and leader routing are placement geometry, not Scene repair. The 2em bound applies to completed text on both sides; leader failure follows declared candidate/suppression semantics. Existing full-band preflight must remain consistent with final candidates. |
| Scene and adapter (Spec 08) | Scene only projects completed leader and warnings. SVG does not compute distances or reroute. Raw SVG and Scene output must both be inspected. |
| Diagnostics (#450, Spec 08) | A single successful-render warning ledger prevents CLI/Scene divergence; preliminary Scene evaluation is acyclic, final Scene includes perceptibility facts. Existing detailed `fitWarnings` remain available. |

No schema migration is needed. Public resource byte changes and new warning strings are intentional; #497 is excluded. Risks to review during implementation: routed leaders may change the obstacle set for later labels, a duplicated Project title may need deterministic disambiguation, and diagnostics order must remain stable. If these cannot be satisfied without new policy, return to design and publish a correction before code.
