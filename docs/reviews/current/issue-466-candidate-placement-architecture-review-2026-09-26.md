# Architecture Review — Candidate Placement (#466)

**Design:** [candidate placement](../../design/issue-466-candidate-placement-design-2026-09-26.md). **Plan:** [candidate design plan](../../planning/active/issue-466-candidate-model-design-plan-2026-09-26.md). **Published prerequisite:** [O2 acceptance](issue-466-shared-obstacle-prerequisite-acceptance-review-2026-09-26.md), green at `96a16aa4` and reviewed at `e2c75976`. **Decision:** approve the versioned candidate/source-reference contract for implementation planning, subject to the migration and proof gates below; this is not an implementation acceptance.

## Whole-architecture consistency

| Authority | Check and conclusion |
| --- | --- |
| Project and [Spec 02](../../specification/02-domain-model.md) | Project annotation ID, object anchor and narrative remain semantic facts. View's presentation reference does not edit or retype the Project note. Missing or filtered IDs fail instead of falling back to text matching. |
| View and [Spec 06](../../specification/06-view-model.md) | A stable View-local annotation ID selects source, facet/endpoint, purpose and candidate order. v0.23 changes authoring syntax deliberately; v0.22 remains separately parsed and normalized. There is no pixel coordinate in View. |
| Style/Theme and [Specs 07](../../specification/07-style-and-theme.md)/[26](../../specification/26-presentation-theme-expression.md) | Theme supplies finite appearance/tail dimensions, not a search or anchor. The selected treatment enters Layout before collision evaluation. Existing resolved Theme identity and font metric ownership remain unchanged. |
| Layout and [Specs 33](../../specification/33-intent-oriented-layout.md)/[44](../../specification/44-usable-explicit-rows-and-annotation-rail.md) | One shared obstacle index and O2 route-priority phases remain. A legacy rail is one normalized candidate, never a second router. Row/background decoration is not a hard obstacle. Box and connector commit together. |
| Scene/adapters and [Specs 08](../../specification/08-scene-and-rendering.md)/[50](../../specification/50-constraint-driven-gantt-surface-quality.md) | Scene projects completed box/Path/text/decision provenance. SVG/typeset serialize Layout path commands and existing paint roles; PNG is derived. No font measurement, search, routing or fallback is moved into an adapter. |
| Related issues | #413's purpose-independent ladder survives as candidate order; #449's visible completion survives exhaustion. #467's lane packing must consume the same mark/label obstacle phases and cannot run a separate note search. #465 image-backed notes are outside this treatment. |

## Alternatives rejected

Copying Project note text into View would make one narrative have two authorities and hide source edits. Inferring View purpose from Project `kind` would make semantic data select presentation. Treating a plot balloon as an adapter SVG decoration would bypass obstacle checks and break typeset/PNG parity. Reusing the current `notes` slot while drawing a second plot note would duplicate visible text. Adding nearest-free as another conditional in `surface_composer` without typed candidate data would preserve the very per-rung ownership defect this issue addresses. Retaining an old v0.22 side field in v0.23 would create two competing orders; the new version deliberately uses candidates only.

## Migration and remaining risks

- The v0.22 normalization slice must be byte-identical against the O2 public materializers before the new resource is exercised. Any changed byte there is a regression, not a permitted design migration.
- HALCYON 02's v0.23 View, new Theme treatment and no-rail Layout must publish atomically. New schema, authored resources, generated Scene/SVG and contrast/font reports belong in that release unit. Other contexts stay materializable throughout.
- Tail geometry is collision-sensitive: the measured box, integrated filled tail and edge strokes must be checked together. If the three-note acceptance fixture cannot be satisfied within the finite declared search, stop implementation and publish a design correction; do not widen a hidden limit or drop an obstacle class locally.
- `searchCount` is the number of joint box/connector trials. Structural tests must assert exact deterministic counts on a neutral fixture and bounded counts on public examples. A later candidate diagnostic must name the selected ID.
- The source-reference path requires a stable missing/filtered-reference diagnostic and provenance through Scene. Tests must prove unselected Project notes still use the notes slot, selected notes appear exactly once, and deleting a View annotation leaves Project unchanged.
- Theme v0.12 and View v0.23 are intentional public migrations. Existing v0.22/v0.11 resources remain valid for characterization, but new resource syntax does not acquire a compatibility shim that undermines typed candidates. Record updated schema inventory, resource closure and migration examples.

## Review outcome and gate

The design is consistent with the Project → View → Theme → Layout → Scene → adapters boundary after the linked living-specification updates. No unresolved ownership conflict authorizes code changes outside the [implementation plan](../../planning/active/issue-466-candidate-placement-implementation-plan-2026-09-26.md). Implementation planning must enumerate exact schema/resource owners, neutral and HALCYON tests, rendered SVG/PNG evidence, materializer byte parity, generated reports, CI matrix and seven literal issue criteria. The design and this review must be public before product implementation begins.
