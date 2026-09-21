# M27 I27-R6 Rich Primitive Design Review — 2026-09-21

**Decision:** Design complete; R6 implementation is authorized.

Specification 37 now closes the two omissions found during acceptance review. Role
typography is fully derived from declared Theme v0.2 bindings, while layout metrics
remain geometry inputs rather than hidden style defaults. Existing object annotation
anchors resolve to projection marks, then use the completed Layout Manifest and
finite router for bounded leaders. Dependency markers are named Theme tokens carried
by completed Scene paths and serialized only when referenced.

The design keeps the deleted Settings/legacy Theme contracts absent. It adds no
example branch, no raw adapter input, no authored coordinates, and no parallel layout
grammar. The R6 execution plan requires focused evidence plus materializer,
conformance, and full-suite verification before #29 and #33 can close.
