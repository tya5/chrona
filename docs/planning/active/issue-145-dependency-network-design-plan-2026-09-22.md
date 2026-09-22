# Issue 145 Dependency-Network Surface Design Plan

## Objective

Add a dependency-network (PERT) View surface derived from the existing render
closure, while proving that the Layout → Scene → renderer boundary supports a
second surface without a second rendering pipeline.

## Authoritative starting facts

- View v0.7 has one implicit table/timeline surface.  Its schema and typed
  contract expose no surface discriminator.
- `render_review` builds one projection/content/measurement input and invokes
  `compose_review_surface` directly.
- `compose_review_surface` requires `title`, `table`, `timeline`, and
  `timeline-axis`, and `compose_surface_layout` allocates rows, time scales,
  marks, and timeline relations directly.
- Layout placement records can already carry `Rect`, `Text`, and `Path`
  geometry, and SVG already serializes those primitive kinds.
- The semantic registry is the sole public vocabulary for current Scene
  purpose/role mappings; Layout Profile slot sources are likewise a closed
  registry-backed vocabulary.

## Design questions

1. Decide whether a narrow, renderer-neutral surface dispatch boundary can be
   introduced below `render_review`, or whether the fixed review composer is a
   confirmed architecture gap that must be corrected before the PERT feature.
   No hidden use-case switch or renderer-specific branch is permitted.
2. Specify View ownership: `surface: table-timeline | dependency-network`,
   which existing View fields apply to each value, and which fields are
   deliberately rejected rather than silently ignored.
3. Specify typed network placement closure: node identity/title/bounds, input
   and output ports, completed or suppressed routed edges, rank/order facts,
   and no raw Project mapping in Layout or Scene.
4. Specify deterministic layout policy: graph validation, longest-path ranks,
   stable intra-rank ordering from the View ordering contract, node sizing from
   measured text, orthogonal routes, port allocation, collision/viewport
   invariants, and declared overflow diagnostics.
5. Specify Scene semantics only after the geometry contract is fixed:
   `networkNode`, `networkEdge`, and `criticalEdge`, all mapped to existing
   Rect/Text/Path renderer primitives and Theme tokens.
6. Specify a Layout Profile slot/source strategy that lets an author choose a
   network-only or combined composition without making a table/timeline source
   mandatory for a network surface.
7. Review all decisions against Project → Scheduler → View → Layout → Scene →
   Renderer ownership.  If a second surface requires a use-case, closure, or
   renderer change, publish that finding as a prerequisite architecture
   correction before implementation.

## Planned publication units

1. This design plan.
2. A detailed English design and architecture-consistency review, including
   the result of the dispatch-boundary investigation.
3. An implementation plan with independently reviewable contract/dispatch,
   Layout/Scene, and HALCYON release-gate slices.
4. Only then, implementation PRs with focused tests, full pytest, public
   materializer checks, generated SVG review, CI, and serial merge.

## Design acceptance

- The final ownership model names one owner for graph semantics, placement,
  primitive projection, and target serialization.
- A network surface cannot silently reuse timeline geometry or authoring
  fields that do not apply to it.
- The design proves either that the existing seam is sufficient or identifies
  the minimal prerequisite correction with its own acceptance criteria.
- Any extension preserves deterministic output and the current output-quality
  gate for every surface.
