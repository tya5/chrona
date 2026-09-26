# Design Amendment — Fit Specification Supersession (#457)

**Predecessors:** [original fit design](issues-457-447-fit-and-host-font-design-2026-09-26.md), [residual-fit correction](issue-457-residual-fit-correction-2026-09-26.md).

The architecture-wide L2 review found older normative prose in Specifications
08, 28, 33, 43, and 44 that still requires a fit refusal. The newer #449/#457
completed-geometry rule cannot coexist with those sentences. This amendment
states the supersession explicitly: for every valid current Draft or immutable
presentation closure, measured geometry that exceeds a requested slot or
viewport completes visibly with Layout-owned warnings and canvas expansion.
The historical `diagnose` slot spelling is not permission to reject a valid
shortage. Explicit optional clipping, suppression, and feasible ellipsis
retain their authored semantics; a required representation that cannot fit
even its compact minimum remains visible. Invalid resource structure,
contradictory authored constraints independent of viewport, absent required
measurements, and nonpositive viewport still diagnose.

Specification 08's older Scene measurement and output-overflow prose is not
current ownership for v0.5 review surfaces. Layout owns physical placement
and completed canvas; Scene and SVG only project them. Specifications 28/43/44
must defer to this rule for detail panels, title measurements, rows, and
annotation rail. Specification 33's diagnostic table must distinguish
invalid authored constraints from ordinary shortage and mark
`E_LAYOUT_REQUIRED_OVERFLOW` as retired for valid current rendering.

The immutable path must not invent a Draft-only exception or rematerialization
hint for a fit shortage. The old `E_LAYOUT_REQUIRED_OVERFLOW` translation in
the render use case is dead after Layout removes that producer and should be
deleted. No schema or resource identity changes are required.

## Whole-architecture review

ADR-0031, Specifications 08/13/28/30/33/43/44/50 and #449 are consistent
once the above supersession is recorded. Layout retains text/icon/row/route
geometry authority; Review Detail and Theme retain content/policy authority;
Scene and adapters do not recover geometry. The published public corpus must
stay byte-identical at its authored viewports; narrow outputs gain only
completed extents and warnings.
