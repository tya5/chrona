# ADR-0028: Completed SceneSurface Is the Only Review SVG Input

**Status:** Accepted — 2026-09-21

## Context

The current `render-review` path resolves an immutable Render Context but then creates
a reduced `ReviewScene` and serializes it through `table_timeline`. This bypasses the
completed `SceneSurface` contract already owned by Specifications 08 and 30. It loses
declared presentation families and introduces serializer-local typography, axis, and
table-value behavior.

## Decision

The public Review SVG route MUST construct one completed `SceneSurface` from
`ResolvedPresentationInput`, the resolved Layout Manifest, and explicit font metrics,
then serialize it exclusively through `render_scene_surface_svg`.

`table_timeline` and `ReviewScene` are not public product contracts. During M27 they
may exist only while their generic mechanisms are migrated or tested; they MUST NOT be
reachable from `render-review`, selected by a profile, or used as a fallback. M27 does
not add an output target or preserve old SVG bytes as a compatibility obligation.

## Consequences

- Scene construction, rather than an SVG adapter, owns all geometry, text measurement,
  row/group policy, axis intervals, table display strings, markers, patterns, and
  routes.
- Theme and Color Scheme values are resolved before Scene construction. SVG serializes
  completed token values and has no presentation-policy defaults.
- A declared Layout slot is either populated by its complete Scene family or rejected
  with a stable input/overflow diagnostic. Empty reserved slots are prohibited.
- Existing helper modules may be reused only through the completed Scene Builder. Code
  duplication or example/preset-ID branches are prohibited.
- Example artifacts are regenerated only after the new public path passes the M27
  reproduction contract.

## Alternatives rejected

1. Reintroduce the old serializer beside the new path: rejected because it creates two
   product semantics and hides divergence.
2. Add missing features directly to `table_timeline`: rejected because it would repeat
   the completed Scene/serializer model and retain adapter-owned policy.
3. Keep a reduced feature set and revise specifications: rejected because declared
   generic resources and renderer-neutral primitives already own the missing behavior.
