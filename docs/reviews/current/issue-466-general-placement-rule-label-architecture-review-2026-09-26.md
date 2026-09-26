# Architecture Review — Rule-Label Host Exemption (#466)

**Reviewed:** [correction](../../design/issue-466-general-placement-rule-label-correction-2026-09-26.md) against Specifications 06, 08, 33, 38, 44 and 50, #449 visible overflow and the #466 typed inventory.

The rule and its label are both Layout placements with stable IDs. Naming their host relationship in the inventory preserves a single collision authority; omitting the rule from the entire label/annotation phase would violate it. Restricting the exemption to the as-of label's own rule does not change View semantics or give Scene/adapter a placement decision. Other labels and annotation connectors retain the barrier. Accepted as an O2 design correction. Test an unchanged as-of-label byte on a neutral and the public aster-ssd fixture, and a note that still cannot cover/cross the as-of line.
