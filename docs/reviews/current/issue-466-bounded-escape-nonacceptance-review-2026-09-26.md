# Non-Acceptance Review — O2 Annotation Route Topology (#466)

**Public base:** `07f55068` contains the bounded-escape design, not product implementation. The O2 code and regenerated artifacts remain unpublished experiments.

The controller-z annotations integration assertion passes after a finite perimeter escape, but the rendered SVG visibly wraps `bringup-risk` around the slide's top, left and bottom edges (approximately `y=26`, `x=22`, `y=1153`). That is not an acceptable annotation connector. Without the escape, the 1024-state router falls back to a direct diagonal that intersects content. A diagnostic 32768-state search found the same outer route within the declared 8-bend/2× policy; therefore the failure is not simply an inefficient A* tie break.

The accepted shared inventory shows the actual topology: a prior firmware leader and dependency path separate the bring-up mark from the rail box; required/optional text and marks further constrain the local corridor. Excluding all text and connector obstacles can produce a shorter path, but contradicts #466's motivating guarantee that notes/leaders avoid marks, labels and dependency lines. Neither an unreviewed obstacle-class exemption nor a perimeter-only route is a clean resolution.

**Decision:** reject the perimeter escape as an O2 acceptance solution. Do not publish the experimental O2 product code or generated evidence. Reopen design of connector/annotation placement interaction under the [topology design plan](../../planning/active/issue-466-annotation-route-topology-design-plan-2026-09-26.md). The previously published [escape design](../../design/issue-466-general-placement-bounded-escape-correction-2026-09-26.md) is superseded for product implementation. #466 and #467 remain open; O1 typed inventory is the only published product slice.

Focused evidence: `test_obstacles.py` and `test_ports.py` passed locally; controller-z integration passed on the experimental generated SVG, but its visual review failed. No CI acceptance is claimed for unpublished product code.
