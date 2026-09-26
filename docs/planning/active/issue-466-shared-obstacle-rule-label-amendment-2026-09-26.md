# Implementation Amendment — Rule-Label Host Exemption (#466)

**Amends:** [obstacle-only plan](issue-466-shared-obstacle-prerequisite-implementation-plan-2026-09-26.md) and [anchor-port amendment](issue-466-shared-obstacle-implementation-amendment-2026-09-26.md) after the [rule-label correction](../../design/issue-466-general-placement-rule-label-correction-2026-09-26.md).

O2 must add a typed rule-host exemption to the shared obstacle query, pass it only for the named as-of label, and keep all other rule collisions active. Add focused positive/negative query tests and characterize the existing as-of label in public aster-ssd output. Re-run public materializer bytes and inspect the complete Scene/SVG diff batch before acceptance. No `W_LAYOUT_LABEL_OVERFLOW` from the rule's own label is accepted as a consequence of this refactor alone.
