# Issue1397 — remaining deadline presentation

Status: design planning. Published baseline: main `e079e0edf`.
Authority: [reviewer assignment](https://github.com/tya5/chrona/issues/1397#issuecomment-6233959539),
which reopens the earlier row4/5 dispositions. Rows1/3 are released; row2 remains
reviewer-owned. The [literal review](../../reviews/current/issue-1397-deadline-captions-acceptance-review-2026-10-15.md)
retains all five issue rows and their evidence.

## Literal scope

| Row | Literal issue text | Required decision/evidence |
| --- | --- | --- |
| 4 | **A deadline mark on the dependency-network surface** (it has no timeline, so the View refuses the member) and per-object overrides of the `show` rule. | Decide network meaning independently of object selection; prove overrides with neutral slipped/kept/absent/unknown/hidden cases. Do not invent a date position on a non-temporal axis. |
| 5 | **Folded header points** carry no deadline mark (`I_LAYOUT_DEADLINE_FOLDED`); a mark on the compact header row is a separate Layout decision. | Decide whether the existing date-positioned tick/run can be hosted safely; prove compact-header allocation, labels, provenance, outlines, and ordinary/folded parity. |

## Design plan

1. Inspect Spec06 selection, Spec33/50 Layout geometry, network surface authority,
   the View schema/default closure and existing folded point allocation.
2. Decide a project-independent use case and contract for each row. A network
   date mark needs a meaningful position rule; if none follows from current
   semantics, propose a precise deferral rather than repurposing graph geometry.
3. Keep Core deadline verdict/date facts immutable, View selection independent
   of geometry, Layout the only geometry owner, and Scene/adapters projections.
   Check forecast, shared/folded occurrences, captions, paint/contrast and labels.
4. Publish selected design/architecture review and affected normative sections
   before implementation. No schema-version bump for additive optional fields.

## Implementation planning boundary

Finalize after design: owned files, independent slices, schema migration,
focused tests, generated evidence and literal acceptance. Likely owners are
View contracts/schema, application deadline selection, Layout deadline/folded
allocation and synthetic integration tests. No `examples/**` edits.

Each implementation slice requires neutral rule tests, batch SVG/Scene counts,
actual PNG inspection for visible geometry, conformance and the repository's
required exact-review-containing main three-OS release before acceptance.
Use the worktree's `.venv`; do not duplicate full pytest locally.
