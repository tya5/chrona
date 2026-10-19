# Issue 1763 — stub/member reservation acceptance

Candidate, not release acceptance. Design/architecture/implementation plan:
[issue Status](https://github.com/tya5/chrona/issues/1763#issuecomment-6256782022),
published before code; normative clarification `a37a5393b` in Spec 50.
Implementation `eb89d2a58`, normally merged ready main `8087e95c5` at `efbaa3a99`.

| Literal acceptance | Status | Direct evidence |
| --- | --- | --- |
| A synthetic stub/member-name case and the public fixture render succeed with no text overlap, focused recovery/label tests and normal release gates pass. | local behavior/focused tests met; release pending | `test_stub_member_reservations.py`: minimal synthetic case and unchanged `routing_revision/project-v1.yaml` with actual default preset, previous Scene and `unroutable: stub`, under both `first-fit` and `best`. All emitted text boxes checked pairwise; required terminal text matched to exact actual SVG text nodes. The `spec` member name is visible or has explicit suppression, not silently lost. Latest-ready 119 focused tests passed in 9.73 s. CI/full public materializers and exact-main three-OS gate remain pending. |

[Actual default-preset SVG raster](assets-1763/stub-recovery.png) inspected:
paired captions are readable, no text collision or clipping observed. Both
policies produce identical SVG bytes, SHA256
`5aa34a7a71b663d736be7d7be1239ece3e45a1f402fecdb36c0c610cdf83091b`.
The original stub render failed the correct overlap guard; the normal-route
reference is not presented as a successful pre-fix stub image.

Architecture review: one Layout coordinator reserves actual terminal text
before optional member names and places ordinary relation labels afterward.
Hard text/label-visual filters apply to visible fallbacks, including group
headers. Legitimate plot/canvas overflow and declared unsafe route-ink policy
remain unchanged. No overlap assertion, quota, source fixture or corpus edit.
No Scene/adapter placement change. Terminal failure carries completed routing
facts as a typed outcome: a first-pass failure is diagnosed; a retry-only
failure retains the valid first result and every executed retry receipt.
Tests cover that retention, unrelated-error propagation, impossible terminal
placement, phase order and existing required member-label behavior. All prior
invalid-input assertions are retained.

Focused batch: `test_presentation_labels`, `test_surface_relation_label_search`,
`test_surface_route_label_plan`, `test_surface_route_label_plan_point_repair`,
`test_surface_route_label_stroke`, `test_member_label_required_phase`,
`test_member_label_route_obstruction`, `test_revision_launch_trial`,
`test_revision_route_corridor`, and `test_stub_member_reservations` (119 passed).
Full local pytest is not duplicated; CI owns the planned full release gates.
