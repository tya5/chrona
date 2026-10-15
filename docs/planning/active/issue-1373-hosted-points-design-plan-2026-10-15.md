# #1373 row 3: hosted point marks — design plan

Baseline: published READY `7c46a7c695ed0863d17998acad062923f7acc4e1`.
Owner: dev A. Design preparation only; implementation follows #1397 row 3.
Authority: [issue](https://github.com/tya5/chrona/issues/1373) and
[reviewer decision](https://github.com/tya5/chrona/issues/1373#issuecomment-6184233415).
The older [backlog note](backlog-slices-1397-1373-1047-2026-10-14.md)
is not the current contract where it conflicts with that decision.

## Literal acceptance and scope

> **Nested milestone inside a capsule.** The reference draws a gate inside its parent bar; chrona draws a free-row mark. Needs: a mark placement rule (a point mark hosted by a span mark) in Layout's mark geometry.

Reviewer-approved boundaries: opt-in Layout Profile policy, off by default;
eligible declared `attachesTo` before eligible direct Project `parent`, no
grandparent traversal; same temporal facet and source; original semantic
interval inclusive; absent, outside or unselected hosts leave the point unchanged.
This changes physical mark placement, not View row membership.
Issue rows 1, 2 and 6 remain separate acceptance rows in the final issue review;
their published implementation and release evidence must be verified before closure.
Reviewer adoption of preset YAML is not a developer closing condition.

## Published facts and unresolved design

- `ReviewItem.parent_id` carries Project hierarchy; `attached_to` is a derived
  row/lane fact, including predecessor attachment, not the original declaration.
  Design must preserve the author link independently and for each source.
- `compose_item_marks` completes point paths, symbol parts and ports.
  `compose_surface_marks` closes their window visibility before labels, routes,
  obstacle indexing and final lane emission. Hosting belongs in that Layout path.
- Lane emissions account for the original child identity. Moving a glyph must
  not leave stale paths, ports, window records, label anchors or collision bounds.
- Settle exact profile grammar and typed normalized policy; do not overload View.
- Settle occurrence identity when an object has several selected comparisons,
  physical block placement, paint ordering and actual-ground contrast.
- Keep date-derived inline coordinates truthful, including inclusive endpoints;
  distinguish semantic containment from full glyph containment. Define this
  explicitly before implementation rather than silently clamping dates.
- Check folded/header marks, hidden rollups and explicit windows against existing
  visibility contracts. Do not introduce a hidden host or bypass a contrast gate.

## Design and publication sequence

1. Complete design and whole-architecture review against Specs 06/07/08/33/38/49/50/56:
   source identity versus row membership, Theme treatment versus Layout geometry,
   visibility/ports, Scene projection, schema extension and migration.
   Publish selected design and normative specification before implementation.
2. Publish implementation plan: source-link projection, profile schema and
   normalization, Layout composition/closure, synthetic tests and acceptance review.
   Identify touched files shared with dev B before changing them.
3. After #1397 row 3, implement one coherent feature PR. No `examples/**` edits,
   manually generated evidence, new row packing policy or adapter-side placement.
4. Focused tests: default-off identity; each qualifying link and precedence;
   inclusive endpoints; missing/outside/unselected hosts; planned/Actual/snapshot/
   scenario isolation; duplicate occurrences; ports/paths/glyph parts; window and
   lane closure; labels/routes/contrast; actual rendered SVG and typeset output.
   Run schema equivalence and inspect public SVG/Scene deltas as one batch.
5. CI supplies full pytest/conformance/materializer evidence. Accept every literal
   issue row against published code, rendered artifacts and the exact review-containing
   main three-OS release; close only when all developer-owned rows are met.

No new diagnostic, ambiguity fallback, paint exemption or geometric fit policy
is approved by this plan. Resolve those in design if needed.
