# Issue 1397 row 3 — design plan

Status: design and architecture review complete; no caption implementation. Public baseline:
`d5564a346c7b91335e4e58379a7b9d7e0e7ea7ef`.

## Authority and scope

Literal row: **A "days late" caption next to the run**, through the #586 figure
vocabulary and its format rules (locale and unit word are author text there).
`W_DEADLINE` already states the number.

[Reviewer decision](https://github.com/tya5/chrona/issues/1397#issuecomment-6182798308):
one closed `{daysLate}` placeholder, slipped deadlines only, the other side of
the tick on overflow, and counted `I_LAYOUT_DEADLINE_CAPTION_DROPPED`; no general
per-object figure scope. Deliver formatting and placement together.

Other issue rows remain separate: row 1 is PR1521; row 2 is reviewer-owned;
row 4 is parked pending a network position rule; row 5 is declined. This slice
does not close the parent issue or change `examples/**`.

## Published baseline and unverified points

- Core `DeadlineStatus.days_late` is the authoritative calendar-day difference.
  The current `ReviewDeadline` drops that value; Layout emits tick/run paths only.
- Count formatting and closed template parsing already exist in Presentation.
  The figure model has global/group scopes, not a per-object deadline scope.
- Layout owns text metrics, placements and its monotone obstacle inventory;
  Scene projects completed text. Ground text has a 4.5:1 contrast requirement.
- [Dev B's draft](https://github.com/tya5/chrona/tree/wip/issue-1397-row3-caption-note)
  is input, not implemented behavior. Its suggested 3:1 mark ink must be reconciled
  with the existing text contract before code.

## Design questions and review order

1. Close the optional View caption contract, shared format schema, invalid
   template/format diagnostics, runtime defaults and typed normalization.
2. Pass the Core count into Presentation without recomputation; expand author
   text before Layout. Define stable object/host identities and provenance.
3. Select a Theme text-role contract that supports project tuning without
   weakening contrast or requiring changes to every existing Theme.
4. Specify Layout candidate anchors, measured gap, plot containment, collision
   priority, obstacle registration and counted omission. Keep this separate
   from row allocation and deadline tick/run geometry.
5. Review against Specs 04/06/07/49/50/56 and the existing figure, typography,
   semantic registry, routing and adapter boundaries. Publish the design and
   architecture review, then finalize the implementation plan before code.

Selected contract: [design](../../design/issue-1397-days-late-caption-design-2026-10-15.md);
[architecture review](../../reviews/current/issue-1397-days-late-caption-architecture-review-2026-10-15.md).

## Required acceptance evidence

| Criterion | Evidence to collect |
| --- | --- |
| Literal row and approved closed placeholder | Actual SVG text equals the Core late count in author copy; all four existing count forms and literal braces tested. |
| Slipped only | Kept deadlines under `show: all` retain marks without a caption. |
| Right side, then other side, then counted drop | Synthetic geometry and actual SVG prove candidates, containment, collision avoidance and per-occurrence diagnostic/provenance. |
| No caption means unchanged output | Default-off synthetic bytes and one batched public SVG/Scene snapshot comparison. |
| Whole-architecture consistency | Published boundary review; Layout-to-Scene projection tests; no adapter measurement or Core presentation policy. |
| Release | Focused tests, schema equivalence, CI conformance/full three-OS release and newest-Python public materializers on the exact published commit. |

No migration of existing authored resources is intended. Public schema additions
must be optional in place (Spec 56); inspect generated reports instead of editing
them. The next publishable unit is the completed design, not partial formatting
code with no visible caption.
