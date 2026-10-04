# Issue #1114: primary-mark-safe route completion

Public baseline: `345e5773`; safety-only PR #1138 includes the replacement-jog
correction `775661f0`. This is the archived design/review/implementation record.

## Scope and owner disposition

The [owner decision](https://github.com/tya5/chrona/pull/1138#issuecomment-5979291459)
withdraws exact preservation of existing compliant routes. Changed routes and
displaced/suppressed labels are accepted costs of the safety fix, disclosed
per slide in the PR. All other literal safety acceptance stands. Do not
mitigate these costs here: corridor admission, alternative path search,
node-aware ordering and route simplification belong to consolidated #1109.
No examples edits, new routing budget, or project-specific geometry rule.
The superseded partial-corridor proposal is not part of this release.

## Selected design and whole-architecture review

Layout excludes temporal egress through a mark and validates primary-mark
interiors after lane/non-lane repair, back-route completion, rounded paths and
diagonal fallback. Endpoint authorization covers only the outward terminal
stub, not a body route through its host. Scene observes completed paths;
adapters serialize them. Specifications 33/50 remain the geometry authority.
No schema, Theme, View, resource identity or adapter behavior changes.

Replacement-jog validation occurs before accepting a repair, not only after
choosing its first candidate. A neutral target rectangle `(0,90,10,100)` with
points `((20,110),(0,110),(0,90),(0,95))` rejects the existing x=8 jog and accepts
the existing x=12 jog. Validate newly replaced segments, retain the final
whole-path guard and existing jog/port order, bounds and quality budgets.
An already compliant first repair remains identical. No joint solver.

## Implementation and release plan

1. Publish this narrowed design/review/plan and remove the unimplemented
   partial-corridor rule from Spec 50. Preserve its WIP separately for #1109.
2. Align the Editorial generated-Scene test with owner-approved safety rather
   than obsolete no-loss acceptance. Keep name association/reach assertions;
   assert no through-mark finding and an exact suppression diagnostic for
   every omitted declared dependency. Do not edit generated examples.
3. Run focused safety/ports/repair/Editorial tests locally. CI supplies one
   public Scene/SVG snapshot, full PR shards and reproduction. Review its
   per-slide route, label/name/index and new fallback counts in the PR body.
4. Merge the exact green head under publication coordination, then publish
   the literal acceptance review and cite exact-main three-OS release evidence
   before closing. Finish this issue before resuming #1130 or #1088.

| Literal acceptance | Evidence required |
| --- | --- |
| start-to-at, and start-to-start, with the target to the right; | Neutral Scene safety fixtures. |
| the mirrored end-to-end case with the target to the left; | Neutral Scene safety fixture. |
| a bar with no free gap above, and one with no free gap below. | Neutral blocked-side fixtures. |
| For each, no relation segment overlaps the interior of any bar by more than the stroke width, and the first segment leaves the port outward. | Completed-path interior/outward assertions. |
| A Scene check counts own- and foreign-bar crossings corpus-wide; it must be 0 after regeneration. | All public Scene snapshot findings. |
| On target B, `avionics-cdr` no longer crosses the Avionics bar. | Current target-B Scene and actual SVG. |

Withdrawn row: “Existing compliant routes are unchanged.” Side effects are
disclosed, not silently waived or repaired by corpus edits.

Closed with main commit [8420d007e5d0881bb3ac6e97f5a1cf9203e00f58](https://github.com/tya5/chrona/commit/8420d007e5d0881bb3ac6e97f5a1cf9203e00f58), exact-SHA [derived-main/ready](https://github.com/tya5/chrona/actions/runs/37202949335), and [three-OS release gate](https://github.com/tya5/chrona/actions/runs/37203065647).
