# Issue 254 Advanced-Contract HALCYON Example Design

**Design-plan authority:**
`docs/planning/active/issue-254-advanced-contract-example-design-plan-2026-09-22.md`

## Decision

Add one `flight-readiness` table-timeline slide to the public HALCYON
materialization.  It is an integration example, not a new product contract:
it composes the released Project v0.5 and View v0.8 vocabulary and reuses the
existing SVG target, briefing theme, and wallboard Layout Profile.

The Project gains a small rollup subtree rooted at `flight-readiness`.
`integration`, `vibration`, `tvac`, `emc`, and `psr` become its children in
their current authored order.  The root is a `group` with
`schedule: {mode: rollup}`; it therefore derives its envelope from existing
scheduled descendants and introduces no scheduling constraint.  The root and
its children receive unique WBS labels, and the selected work items declare
planned progress.  `psr` receives an absolute typed link.

The new View selects this tree through `grouping: {by: hierarchy, depth: 1,
rollup: bar}` and renders the root and its direct children.  Its table makes
the semantic evidence visible through `wbsCode`, `totalFloat`, and `title`
columns; `visibility.links: title` exposes the single Project-owned PSR link
only on its title cell.  It compares the primary plan with the existing
`tvac-slip` Scenario and renders only derived critical dependency relations.

## Authored resources

| Resource | Change | Ownership rationale |
| --- | --- | --- |
| `project.yaml` | Add the rollup root, parent edges, unique WBS labels, declared planned progress, and the PSR link. | Hierarchy, schedule envelope, progress intent, and URL are Project facts. |
| `views/06-flight-readiness.yaml` | Select and expand the tree; choose scenario comparison, critical relations, title links, and visible table sources. | View chooses what facts are present and how they are presented. |
| `contexts/06-flight-readiness.yaml` | Bind the existing source resources and declared font metrics to the SVG target. | A Render Context is the reproducible closure boundary. |
| `manifest.yaml` and `generated/06-flight-readiness.svg` | Register and check in exactly one new public artifact. | The materializer owns reproducible public evidence. |

The current five generated HALCYON SVGs remain byte-identical.  The rollup
root is not selected by their ID-based Views, and their non-hierarchy grouping
does not consume a Project parent edge.  Planned progress and a link are
inert unless a View selects their corresponding vocabulary.

## Boundary and composition review

```text
Project v0.5 facts (tree, WBS, progress, link, scenario, dependencies)
  -> scheduler (rollup envelope and critical/float analysis)
  -> View v0.8 (hierarchy expansion, scenario baseline, columns, visibility)
  -> Layout (row/mark/table/route placements)
  -> Scene (placed primitives and selected link metadata)
  -> SVG (generic primitive and anchor serialization)
```

This is consistent with the typed-presentation architecture review: no raw
mapping is used after closure, no renderer re-derives a Project fact, and the
example does not add a parallel resolver.  It also preserves the dedicated
ownership decisions already made for hierarchy and planned progress (Project),
criticality and total float (Scheduler), Scenario selection (View), geometry
(Layout), and link serialization (Scene/SVG).

`plannedProgress` deliberately has no visual column in this slide.  Its role
here is to exercise validated, typed Project closure beside the rollup; showing
it would require a new View source and violate this issue's no-new-vocabulary
boundary.  The existing closure/schema tests remain the direct assertion that
the values reach their typed record.  In contrast, WBS, float, Scenario title,
critical edges, and the title link each have already-released rendering paths
and are asserted in the public artifact.

## Scenario and relation policy

The View's automatic primary data remains the authoritative Project.  Its
baseline is the named `tvac-slip` Scenario, whose only override remains
`tvac.schedule.amount: 21d`; the scenario resolver constructs and schedules a
derived Project before View projection.  The rollup is consequently derived
in each schedule and no Scenario state is stored in Layout, Scene, or the
renderer.

`relations: {mode: critical, overflow: suppress}` is intentionally a filter,
not a style instruction.  The Scheduler alone determines float and critical
membership; View selects a dependency only when both resolved primary endpoints
are critical; Layout routes it; Scene uses the registered
`dependency-critical` role.  A normal relation must not be promoted merely to
make the example visually busier.

## Acceptance evidence

1. Project/closure characterization asserts the root's derived hierarchy and
   the typed planned-progress/link facts, while preserving current validation
   and schedule behavior.
2. A focused materialization test for `flight-readiness` proves hierarchy row
   identity/depth and WBS/float/scenario table values; it proves exactly the
   selected PSR title primitive carries the expected link metadata; and it
   proves every emitted dependency relation has the critical scene role.
3. The public materializer reproduces all six manifest slides byte-for-byte.
   The generated-output property suite includes the sixth artifact and reports
   no unpinned failures.
4. Focused tests and the full pytest suite pass.  Review compares the five
   existing artifact hashes and the new SVG's semantic primitives, rather than
   treating a regenerated byte difference as sufficient evidence.

## Non-goals and migration impact

No schema version, compatibility parser, renderer target, source vocabulary,
or quality policy changes.  The only public artifact addition is a sixth
HALCYON slide; consumers of existing resources are unaffected.  If a required
assertion reveals a missing released data path, this implementation stops and
opens a design correction rather than adding a test-only shortcut.
