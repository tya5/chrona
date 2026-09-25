# Architecture Review — Table--Timeline Composition (#404, #403, #388, #389, #409)

**Decision:** Accepted, with the constraints below binding on implementation.

## Authority review

| Boundary | Review result |
| --- | --- |
| Specification 02 | Pass. The design keeps Project parent/child hierarchy authoritative, treats WBS as a display field, and keeps View grouping separate. Explicit Review-row nesting remains a presentation composition rather than an attempt to rewrite Project hierarchy. |
| Specifications 24 and 33 | Pass. View declares finite table/decoration intent; Layout measures columns, rows, and cross-slot bounds. No View coordinate, Theme allocation, or adapter layout inference is introduced. Reusing the Layout size grammar avoids a second width language. |
| Specification 50 | Pass with dependency. Required bounds, track containment, and table overflow stay Layout invariants. #400 supplies the common visible/invisible failure policy before P1 changes failure behavior. |
| Specification 55 | Pass. Column alignment, width allocation, hierarchy-column selection, row decoration, and background treatment resolve to View/Theme/Layout owner fields; none creates a preset- or renderer-owned design axis. |
| Specification 63 | Pass after narrowing. `paintOrder` is not a generic target capability or z-index language. It is a finite completed ordering key for P1 background primitives only; adapters project it without interpreting Theme. Blend modes remain excluded. |
| Specification 64 | Pass. P1 does not change icon selection, asset closure, or icon geometry. Future label orientation remains P4 work. |
| Scene/renderer boundary | Pass. Layout completes decorations and ordering; Scene carries them; SVG/PNG serialize. There is no builder-prefix, profile-ID, or corpus-name branch. |
| Reproducibility/migration | Pass. View/theme/profile schema successors and every corpus Context migrate atomically, with no v0.15 compatibility reader. Materializer and installed-wheel evidence remain release gates. |

## Required implementation guardrails

1. Do not parse `wbsCode` to infer hierarchy or reject it because its segments
   differ from a visual depth. Only Project hierarchy traversal defines `path`.
2. `hierarchyColumn` is a View content/presentation selector, never a Layout
   metric; indentation distance remains a Theme/Layout measured value.
3. `fill` column allocation must not bypass `diagnose` or
   `ellipsize-with-source`. A failed required minimum is a Layout diagnostic.
4. `pack` and `fill` may distribute only surplus after the per-row required
   extents have been computed from real track placement.
5. Background validation must inspect completed bounds and resolved alpha,
   not assume that role names or construction sequence demonstrate overlap.
6. Do not generalize P1's background ordering field to marks, relations, or
   arbitrary primitives. Existing completed mark paint ordering stays owned by
   its dedicated contract.

## Review conclusion

The P1 design strengthens the existing Project → View → Layout → Scene →
adapter flow and removes, rather than preserves, the accidental position-zero,
equal-height, and builder-order authorities. It may proceed to an implementation
plan after #400's policy design explicitly supplies the overflow classifications
P1 consumes.
