# Unroutable dependency resolution acceptance (#1427)

Implementation: [PR1447](https://github.com/tya5/chrona/pull/1447),
`d4509cd88160847b95a62ae566b840045c1b6bc3`, based on READY `208cf1cc`.
Authority: [current work plan](../../planning/active/issue-1427-unroutable-work-plan-2026-10-12.md),
Specs08/33/46/50, and [reviewer release decisions](https://github.com/tya5/chrona/issues/1427#issuecomment-6133101361).
Current-head CI [38315016163](https://github.com/tya5/chrona/actions/runs/38315016163)
passes on `43de3ff4`; exact-main three-OS release is required before closure.

| Literal criterion | State | Evidence |
| --- | --- | --- |
| Under `suppress`, every example is byte-identical. The reviewer declares `suppress` on the five approved design targets before the default flips, in the same coordination as #1426's `search: best`. | Locally verified; release pending | Published pre-flip suppress batch:46 full Scene/SVG pairs identical against READY587ff01d. Reviewer `e442bcf5` is integrated as `4dd83d5e` before the atomic flip. Final protected SVGs are identical; Scene changes only the intentionally changed Layout resource contentIdentity, not paint or geometry. Resource provenance is disclosed, not normalized away. |
| Under the default `relax`, the trial's v2 launch plan draws `spec-build`, and every relation of every example slide is drawn. Count the stage used per slide in the PR. | Locally verified; release pending | Actual supplied launch regression passes. All46 materializers complete;527 projected instances are normal, zero added/removed/changed paths, zero recoveries. [Per-slide counts](https://github.com/tya5/chrona/pull/1447#issuecomment-6133177789); declared window absence remains separate. |
| A test per mode on a synthetic plan where one relation is fully blocked. | Locally verified; release pending | `test_unroutable_visible_obstacle.py` paints its completed blocking mark in real Scene/SVG for suppress/relax/overlap/stub. `test_relation_resolution_wiring.py` also checks budget, domain, terminal and fixed-fallback wiring. |
| Halo paint order: the line lies below text in the Scene. The halo is a decoration under the contrast policy. | Locally verified; release pending | Wiring tests assert completed halo/path/text order and SVG projection; `test_contrast_policy.py` verifies decoration classification. Spec46's approved synthetic coverage is explicitly reported only until public use; unrelated missing roles and emitted-paint evaluation remain checked. |
| Do not edit `examples/**`. | Verified for dev-authored scope | Only the reviewer-authored five protection declarations are included, explicitly authorized for the atomic release. No other example edits. |

Verification: focused suites57,32 and24 pass; schema-equivalence against
`origin/main` passes. Earlier broad Layout owner suite2662 passes. Final46-context
evidence: all SVGs identical,45 Scenes differ only in policy/provenance/diagnostic
metadata; network output unchanged. No generated public artifacts/reports are
PR-authored. CI owns the disposable snapshot and full release matrix.

Architecture review: Layout closes routes, terminals, labels, halos and final
receipts; Theme supplies paint; Scene/adapters project completed primitives.
Search budgets remain instance/pass-local, including rejected passes. Critical
priority does not create a separate unsafe-mode contract. Coverage disposition
is repository evidence tooling, not an exception in runtime contrast policy.

CI38312752823 exposed41 failures in the three pytest shards; derived-ready
failed consequentially. Preview/conformance/MCP/newest-Python passed. Repair:
Spec50 correction `3ba05ff5` precedes the corridor predicate change; non-normal
rehearsal recovery now permits existing normal repair first. A relax control
proves a normal path with all names retained. Old conservative controls declare
suppress; no assertions/skips are removed. Three chip/note byte fixtures change
only their explicit Layout resource identity (independent predecessor comparison);
SVG and every other Scene field match. CLI golden changes20 cases only by the
approved supersession info; unrelated argparse quoting is preserved. Current
focused gate332 PASS51.08s. Current CI is successful, including all three pytest
shards, conformance, MCP and newest-Python reproduction. Artifact11775888839
contains45 Scene metadata changes and3 reports: exact primitive identity in
every changed Scene, zero SVG changes/retirements, contrast errors0. No new
product changes follow this validation; verify the containing-review head and
exact-main release before closure.
