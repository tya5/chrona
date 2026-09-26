# Architecture Review — General Placement and Shared Obstacles (#466)

**Reviewed:** [#466 design](../../design/issue-466-general-placement-design-2026-09-26.md)
against Specifications [06](../../specification/06-view-model.md),
[08](../../specification/08-scene-and-rendering.md),
[33](../../specification/33-intent-oriented-layout.md),
[44](../../specification/44-usable-explicit-rows-and-annotation-rail.md),
[50](../../specification/50-constraint-driven-gantt-surface-quality.md),
the #413 correction, #449 visible-fallback rule, #467 dependency, and
current Layout/Scene/adapter code.

## Findings

- Current Specification 06 §9 assigns concrete relative offset to Scene,
  conflicting with the accepted Layout/Scene seam in Specification 08 and
  current code. The living specification is corrected with this design.
- Specification 44 describes rail-box-only obstacles as if normative. The
  new surface obstacle contract supersedes that restricted behavior; its
  rail search remains one candidate, not a separate Layout mechanism.
- A single immutable obstacle snapshot is impossible because later accepted
  labels, routes and boxes become obstacles. One inventory object, built
  once and populated in finite ordered phases, meets the issue's “one set”
  requirement without causal cycles or duplicate per-purpose lists.
- Lane packing needs measured plot labels before final row assignment.
  Dependency routes are therefore completed after labels and query the same
  index to avoid them; annotations query both. This breaks the apparent
  label/route cycle without a hidden retry. New obstacle checks can still
  intentionally move notes or leaders and need batch-reviewed evidence.
  No Scene/adapter patch may repair a collision after Layout.
- Source/object identity, View annotation purpose, Theme paint, Context
  closure and #449 visible fallback retain their owners. The tail is paint
  geometry attached to an annotation, never a Project dependency.

## Decision

Architecture accepted for an obstacle-only implementation plan. The obstacle
inventory/query seam is an independently publishable prerequisite for #467;
it does not satisfy #466's candidate/search/tail acceptance by itself.
The later grammar must be versioned and validated, not smuggled through
legacy strings. Its exact schema, tail primitive and Theme treatment are
unresolved design decisions; they MUST receive a design completion, normative
specification update and whole-architecture review before their product
implementation plan is final. No unresolved ownership question blocks the
obstacle-only slice.
