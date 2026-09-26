# Design Correction — A Rule's Own Measured Label (#466)

**Predecessor:** [shared-obstacle design](issue-466-general-placement-design-2026-09-26.md) and [anchor-port correction](issue-466-general-placement-anchor-port-correction-2026-09-26.md).
**Discovery:** the first shared-inventory Layout composition moved the as-of label into visible overflow because its own as-of rule was newly registered as an obstacle. The public aster-ssd Scene showed `W_LAYOUT_LABEL_OVERFLOW:as-of-label` and a changed label coordinate. This is not a requested user-visible policy change.

The as-of label is a measured child of the named `as-of` rule. During *that label's* placement only, Layout may exempt exactly the rule's own stroke obstacle. The exemption is a typed `rule-label-host` relationship, not a global rule-class omission: item labels, relation labels, annotation boxes and leaders must still see the as-of line when their policy includes rules. The label still avoids marks, other required text, unrelated rules and viewport boundaries. The label's own completed box is then registered for later placements.

This is analogous to an inside label's named mark-host exemption but applies only to the rule it explains. It does not allow a note to cross the as-of barrier. View syntax, Theme treatment and diagnostic policy are unchanged. The O2 public byte comparison must prove the existing as-of label remains at its characterized position unless some *other* newly avoided obstacle justifies a documented move.
