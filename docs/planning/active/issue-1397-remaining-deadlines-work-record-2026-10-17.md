# Issue1397 — remaining deadline presentation

Status: overrides/folded implementation verified; network design correction in progress.
Current published baseline: trusted-ready main `690f3549ff0b61ee15ed85885ad18aacd7cabf31`.
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

## Selected design and whole-architecture review

Spec06 §7.3 defines replacing object overrides, strict unknown-id validation and
folded tick/run support; Spec50 §3.4 defines full painted-envelope reservation.
Use case: compact milestone promises remain visible without unfolding a group.
Core still owns deadline/date/verdict/count; View owns selection, the application
binds facts/copy, Layout allocates complete geometry, Scene/adapters only emit it.
Spec33's ownership table is updated. Captions remain optional, placed last with
their existing counted omission; no new collision exemption or retry exists.
Optional schema addition retains v0.28; absent/empty overrides preserve output.
The intentional change is removal of folded-only omission when deadlines are
enabled. Forecast/shared/ordinary hosts use the same completed geometry rule.
No project condition, copied preset, source mutation or generic figure scope.

Network row4 has a valid general use case: a dependency graph reader needs the
promised date and whether the plan misses it, without a time axis. The earlier
[deferral proposal](https://github.com/tya5/chrona/issues/1397#issuecomment-6234014932)
is not a sufficient disposition: absence of a time axis forbids a date-scaled
run, not a node-attached deadline indicator. No reviewer answer is needed to
investigate that existing authorized use case. Product changes remain paused
until the following correction is designed, reviewed and published.

### Network correction design plan

- Reuse Core deadline/verdict/count facts and View show/override selection;
  close selected node facts and display copy before Layout.
- Select a non-temporal in-node indicator and ISO promised-date label, with
  optional existing authored days-late caption. Decide the kept/slipped shape
  distinction, typography/paint/outline envelope and zero-ink behavior explicitly.
- Measure the entire footer before node allocation; enlarged bounds must own
  ports, route obstacles and normal network overflow. No overlay after routing,
  date-coordinate invention, Scene measurement or unrelated network redesign.
- Review Spec06/07/33/49/50, schema prohibition, source/run identity and actual
  Scene projection. Publish normative correction, architecture review and amended
  implementation plan before any network product code.
- Evidence: neutral kept/slipped/missing/hidden/override nodes, independent
  date/caption identity/provenance, measured footprints and routes, unchanged
  omission output, schema equivalence and actual SVG/PNG in both writing axes.
  Official public counts and full exact-main release remain mandatory.

## Implementation plan

1. **Selection:** View schema/contracts and `render_review._shown_deadlines`;
   optional id→show overrides, unknown-id failure, inherited global rules.
   Neutral schema/ingress/application tests cover all/slipped/hidden, absent
   deadlines, unknown ids, selection, caption/warning independence and defaults.
2. **Folded geometry:** `surface_deadlines`, `surface_marks` and integration
   tests. One shared deadline composer supplies painted bounds to folded packing
   and final placements; reserve inline/block extents before emitting marks.
   Cover kept/slipped, outlines/wobble, multiple/shared points, captions, off-window,
   identity/provenance and unchanged no-deadlines output. Inspect neutral PNGs.
3. **One implementation PR:** code, schema migrations, concise literal review
   and normative changes together. Run schema equivalence against ready main,
   focused suites and conformance; consume one official public snapshot with
   per-slide counts, not hand-edited generated files. Three-OS CI supplies full
   pytest/conformance/wheel/public reproduction/MCP. Accept implemented portions
   only after the exact review-containing main release. Network implementation
   joins this PR after its correction is published; row2's reviewer migration
   and subsequent bundled-role addition remain separate. No `examples/**` edits.

Independent baseline defect: [issue1660](https://github.com/tya5/chrona/issues/1660)
records all-point folding resurrecting ordinary rows, reproduced on published
main without deadlines. Its fix needs resolved-empty row/group ownership, not
a deadline condition. The mixed task/point acceptance does not claim to fix it.

Each implementation slice requires neutral rule tests, batch SVG/Scene counts,
actual PNG inspection for visible geometry, conformance and the repository's
required exact-review-containing main three-OS release before acceptance.
Use the worktree's `.venv`; do not duplicate full pytest locally.
