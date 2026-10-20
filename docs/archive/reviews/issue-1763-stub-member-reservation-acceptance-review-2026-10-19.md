<!-- chrona:literal-acceptance/v1 -->

# Issue 1763 — stub/member reservation acceptance

Implementation and review landed in PR1772. The reviewer closed #1763 in
[comment 6268759405](https://github.com/tya5/chrona/issues/1763#issuecomment-6268759405).
The implementation/design and fixture evidence are summarized in the
[implementation status](https://github.com/tya5/chrona/issues/1763#issuecomment-6256782022);
normative clarification `a37a5393b` is in Spec 50.

| Literal acceptance | Status | Direct evidence |
| --- | --- | --- |
| A synthetic stub/member-name case and the public fixture render succeed with no text overlap, focused recovery/label tests and normal release gates pass. | met | `test_stub_member_reservations.py` covers the synthetic case and unchanged `routing_revision/project-v1.yaml` with the default preset, prior Scene and `unroutable: stub`, under both `first-fit` and `best`. Emitted text boxes are checked pairwise; required terminal text matches exact SVG text nodes. The `spec` member name is visible or explicitly suppressed. The focused recovery/label batch passed 119 tests. [Inspected SVG raster](assets-1763/stub-recovery.png) shows readable paired captions without collision or clipping. |

Both policies produce identical SVG bytes (SHA256
`5aa34a7a71b663d736be7d7be1239ece3e45a1f402fecdb36c0c610cdf83091b`). The
official snapshot audit found all 50 SVGs and 50 Scenes byte-identical across
109 declared paths; no route, label or primitive changes or retirements.

The review-containing main
`9dca9c55a8df0d1e44149a0543fe892366d39930` passed exact
[release39256723703](https://github.com/tya5/chrona/actions/runs/39256723703):
Ubuntu, Windows and macOS full matrix; conformance; wheel/smoke; MCP floor;
and newest-Python reproduction. The reviewer closed the issue after this
release passed.

Architecture boundary: Layout owns the terminal/member/ordinary-label
reservation order, placement and retry receipts; Scene and adapters acquire
no placement responsibility. Existing overlap and invalid-input assertions,
route quotas, source fixtures and corpus data were not weakened or changed.
