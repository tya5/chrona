# Design Correction — Residual Fit Closure (#457)

**Predecessors:** [fit design](issues-457-447-fit-and-host-font-design-2026-09-26.md), [L1 implementation plan](../planning/active/issues-457-447-fit-and-host-font-implementation-plan-2026-09-26.md).

L1 makes normal-flow shortage total. The L2 raise-site audit found another
reachable shortage: an exact icon reservation can consume the entire allocated
inline slot, while the corresponding text is still required. Rejecting this
with `E_LAYOUT_REQUIRED_OVERFLOW` contradicts the total-fit rule. A selected
visual and its text are one measured Layout composition. When their combined
natural width exceeds the allocated slot, Layout retains both at their
natural measured widths, places trailing visuals after the text, records a
typed warning with the combined required and allocated widths, and includes
their bounds in the completed canvas. A declared ellipsis or optional clip
applies only where it can produce a valid representation; insufficient room
even for that representation uses visible overflow for required content.
No visual is scaled to zero and no text disappears because an icon was added.

An exact icon scale or viewport ratio that is nonpositive is invalid Theme or
icon input, not a fit shortage; it diagnoses at that input path. The Draft and
immutable paths use the same Layout implementation. The main fit rule also
applies when a placed label extends before the requested canvas origin:
Layout's completed canvas includes both minimum and maximum emitted bounds,
and the SVG viewBox uses the completed origin and size. Adapters do not repair
geometry. A declared suppress/clip policy remains an explicit author choice.

## Whole-architecture consistency

Specifications 08/33/50 and ADR-0031 keep measurement and placement in
Layout; the visual request and exact icon asset are resolved before Layout,
while Scene receives already completed text and icon placements. No View
syntax or Theme token is changed. Immutable closure remains pinned; Draft
host discovery remains isolated above Layout. This correction narrows only
the meaning of `strict` placement under a valid fit shortage and does not
change invalid schema/reference diagnostics. Existing default-size public
artifacts must remain byte-identical unless a previously hidden shortage is
demonstrated and reviewed.
