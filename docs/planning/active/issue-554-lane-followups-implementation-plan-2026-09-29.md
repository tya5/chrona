# Issue #554 — Implementation plan

**Authority:** [design](../../design/issue-554-lane-followups-design-2026-09-29.md), [architecture review](../../reviews/current/issue-554-lane-followups-architecture-review-2026-09-29.md), Specs 08/38/50. Base PR #562. Each slice is a separate commit/push and focused acceptance check; a discovered contract gap returns to design before code.

| Slice | Owners and changes | Focused acceptance and publication |
| --- | --- | --- |
| 554-A table titles | `presentation/review/v05_content.py`, 03 View, table tests | Single-member title, group title, duplicate-group disambiguation, no generated ID; `Items` absent on 03, Scene/SVG agree. Publish commit. |
| 554-B label association | `presentation/layout/labels.py`, `surface_composer.py`, semantic registry, placement model/Scene projection, tests; follow the [leader correction](../../design/issue-554-member-label-leader-correction-2026-09-29.md) | Paired mark/text on both sides; <=2em or completed source-keyed leader, no crossings of required text/other marks, 26/26 on 02/11/12, pack/non-lane unchanged. Publish commit. |
| 554-C diagnostics | `usecases/render_review.py`, CLI warning emission, Scene serialization/model if needed, CLI/Scene tests | One stable warning identity ledger, including attached-milestones label overflow; compare multisets of emitted CLI and Scene warnings. Publish commit. |
| 554-D closed-day paint | bundled and HALCYON Theme mirrors, starter perceptibility/paint tests | Chart/key >=1.15:1 against completed background, same Scene/SVG paint, no comb outlines; intentional Theme byte changes. Publish commit. |
| 554-E release | public materializer tooling, generated `examples/halcyon-1/generated`, review record | Batch inspect affected Scene/SVG/PNG, run focused tests and public materializers; CI supplies full pytest/conformance/wheel/newest Python. Review every literal criterion and exact main CI before closing. |

No public schema change is planned. Recompute immutable resource identities through public materializers rather than hand-editing Context hashes. Preserve the #497 legend-truncation boundary. Before each push fetch `origin/main`, compare exact diff/commits, and stop on an unexpected update; confirm remote PR state after each push.

### Literal acceptance gate

- [ ] Lane labels show a title: the group title, the member's title for one-item lanes, or a declared lane title. No raw id reaches the rendered table. A constant `Items` column is omitted or declared.
- [ ] A name placed off its own mark (stagger or displaced) either stays within a bounded distance of the mark or gets a leader to it. A Scene check measures label-to-mark distance for every member label, on both sides.
- [ ] Every warning printed by the CLI for a render is also in that render's Scene `diagnostics`, and a test asserts that the two sets are equal.
- [ ] The weekend fill and its legend key pass the starter perceptibility gate.
