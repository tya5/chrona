# Open actual terminal correction implementation plan (#399)

## Entry condition

The mark-composition design and Scene-order correction are published.  The
implementation is paused because inspection found that an open terminal is
not visually projected and an open clip host is rejected.

## C1 — Completed Layout outline

Add a renderer-neutral open-span path constructor and make Layout select it
only for `openUntil: asOf`.  Preserve the resolved start/as-of ports,
role-relative leading radius, lane geometry, and existing warnings.

Acceptance: placement tests prove the outline is bounded, closed, and has a
continuation terminal; a closed actual remains a rectangular placement.

## C2 — Scene and adapter projection

Project an open-span as a `Symbol`; permit a completed `Symbol` outline as a
clip host. Serialize that outline verbatim in SVG graphics and clip paths.
Carry completed placement diagnostics into the inspection Scene without
re-evaluating their triggering policy.

Acceptance: Scene structural tests reject inconsistent treatment/shape pairs;
SVG tests prove an open host's completed path is painted and clips a progress
rectangle without geometry synthesis; render integration tests prove the
missing-as-of warning is observable with no fabricated missing-actual stub.

## C3 — Public evidence and release gate

Regenerate the affected public materializer artifacts, run focused layout,
Scene, SVG, schema and materializer tests, then the complete CI matrix.
Review the generated open actual artifact and verify every #399 acceptance
item before publishing the acceptance review and closing the B issues.
